import asyncio
import math
import unittest
from typing import Dict

from app.schemas.autonomy import LaserScan, MessageHeader
from app.services.autonomy import (
    LidarSafetyEvaluator,
    LidarSafetyService,
    LidarSafetyZone,
    SafetyConstraint,
    TopicBus,
)
from app.services.autonomy.topics import LIDAR_SCAN, SAFETY_STATE


class FakeClock:
    def __init__(self) -> None:
        self.now_ns = 1_000_000_000

    def monotonic_ns(self) -> int:
        self.now_ns += 1
        return self.now_ns


class ConstraintRecorder:
    def __init__(self) -> None:
        self.constraints: Dict[str, SafetyConstraint] = {}

    def put_constraint(self, constraint: SafetyConstraint) -> None:
        self.constraints[constraint.constraint_id] = constraint

    def remove_constraint(self, constraint_id: str) -> None:
        self.constraints.pop(constraint_id, None)


def scan(
    ranges: tuple[float, ...],
    *,
    angle_min_rad: float = -math.pi / 2,
    angle_increment_rad: float = math.pi / 8,
    sequence: int = 1,
) -> LaserScan:
    return LaserScan(
        header=MessageHeader(
            sequence=sequence,
            frame_id="laser",
            timestamp_monotonic_ns=sequence * 100,
        ),
        angle_min_rad=angle_min_rad,
        angle_max_rad=angle_min_rad + angle_increment_rad * (len(ranges) - 1),
        angle_increment_rad=angle_increment_rad,
        range_min_m=0.05,
        range_max_m=12,
        ranges_m=ranges,
    )


class TestLidarSafetyEvaluator(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = LidarSafetyEvaluator(
            LidarSafetyZone(
                front_half_angle_rad=math.radians(30),
                stop_distance_m=0.3,
                slow_distance_m=1.0,
                max_forward_speed_mps=1.4,
                max_reverse_speed_mps=0.8,
                min_obstacle_points=2,
            )
        )

    def test_two_close_front_returns_block_forward_motion(self) -> None:
        decision = self.evaluator.evaluate(
            scan((math.inf, math.inf, math.inf, 0.2, 0.25, math.inf, math.inf))
        )

        self.assertTrue(decision.forward_blocked)
        self.assertEqual(decision.max_forward_speed_mps, 0)
        self.assertEqual(decision.max_reverse_speed_mps, 0.8)
        self.assertAlmostEqual(decision.nearest_obstacle_m or 0, 0.25)

    def test_slow_zone_scales_speed_linearly(self) -> None:
        decision = self.evaluator.evaluate(
            scan((math.inf, math.inf, math.inf, 0.65, 0.65, math.inf))
        )

        self.assertFalse(decision.forward_blocked)
        self.assertAlmostEqual(decision.max_forward_speed_mps, 0.7)
        self.assertIn("nearby", decision.reason or "")

    def test_isolated_close_noise_does_not_form_an_obstacle_cluster(self) -> None:
        decision = self.evaluator.evaluate(
            scan((math.inf, math.inf, math.inf, 0.1, math.inf, math.inf))
        )

        self.assertEqual(decision.max_forward_speed_mps, 1.4)
        self.assertIsNone(decision.nearest_obstacle_m)

    def test_two_close_rear_returns_block_reverse_motion(self) -> None:
        decision = self.evaluator.evaluate(
            scan(
                (0.2, 0.25),
                angle_min_rad=-math.pi,
                angle_increment_rad=math.radians(5),
            )
        )

        self.assertFalse(decision.forward_blocked)
        self.assertTrue(decision.reverse_blocked)
        self.assertEqual(decision.max_forward_speed_mps, 1.4)
        self.assertEqual(decision.max_reverse_speed_mps, 0)
        self.assertAlmostEqual(decision.nearest_rear_obstacle_m or 0, 0.25)

    def test_sensor_transform_is_applied_before_sector_filter(self) -> None:
        evaluator = LidarSafetyEvaluator(
            LidarSafetyZone(
                front_half_angle_rad=math.radians(30),
                stop_distance_m=0.3,
                slow_distance_m=1.0,
                max_forward_speed_mps=1.0,
                max_reverse_speed_mps=0.5,
                sensor_yaw_rad=math.pi,
                min_obstacle_points=1,
            )
        )

        decision = evaluator.evaluate(
            scan((0.2,), angle_min_rad=0, angle_increment_rad=1)
        )

        self.assertEqual(decision.max_forward_speed_mps, 1.0)
        self.assertTrue(decision.reverse_blocked)


class TestLidarSafetyService(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bus = TopicBus()
        self.constraints = ConstraintRecorder()
        self.service = LidarSafetyService(
            self.bus,
            self.constraints,
            LidarSafetyEvaluator(
                LidarSafetyZone(
                    front_half_angle_rad=math.radians(45),
                    stop_distance_m=0.3,
                    slow_distance_m=1.0,
                    max_forward_speed_mps=1.0,
                    max_reverse_speed_mps=0.5,
                    min_obstacle_points=1,
                )
            ),
            scan_timeout_seconds=0.02,
            clock=FakeClock(),
        )

    async def asyncTearDown(self) -> None:
        await self.service.stop()

    async def test_start_is_fail_safe_until_a_clear_scan_arrives(self) -> None:
        states = self.bus.subscribe(SAFETY_STATE, max_queue_size=2)

        self.service.start()
        waiting = await states.get()
        self.bus.publish(
            LIDAR_SCAN, scan((2.0,), angle_min_rad=0, angle_increment_rad=1)
        )
        clear = await asyncio.wait_for(states.get(), timeout=1)

        self.assertTrue(waiting.forward_blocked)
        self.assertTrue(waiting.reverse_blocked)
        self.assertFalse(clear.forward_blocked)
        self.assertFalse(clear.reverse_blocked)
        self.assertNotIn("lidar-directional-zone", self.constraints.constraints)

    async def test_rear_obstacle_only_blocks_reverse_motion(self) -> None:
        states = self.bus.subscribe(SAFETY_STATE, max_queue_size=2)
        self.service.start()
        await states.get()
        self.bus.publish(
            LIDAR_SCAN,
            scan((0.2,), angle_min_rad=-math.pi, angle_increment_rad=1),
        )

        blocked = await asyncio.wait_for(states.get(), timeout=1)

        constraint = self.constraints.constraints["lidar-directional-zone"]
        self.assertEqual(constraint.max_forward_speed_mps, 1.0)
        self.assertEqual(constraint.max_reverse_speed_mps, 0.0)
        self.assertFalse(blocked.forward_blocked)
        self.assertTrue(blocked.reverse_blocked)

    async def test_stale_scan_reinstates_forward_block(self) -> None:
        states = self.bus.subscribe(SAFETY_STATE, max_queue_size=3)
        self.service.start()
        await states.get()
        self.bus.publish(
            LIDAR_SCAN, scan((2.0,), angle_min_rad=0, angle_increment_rad=1)
        )
        await asyncio.wait_for(states.get(), timeout=1)

        stale = await asyncio.wait_for(states.get(), timeout=1)

        constraint = self.constraints.constraints["lidar-directional-zone"]
        self.assertEqual(constraint.max_forward_speed_mps, 0)
        self.assertEqual(constraint.max_reverse_speed_mps, 0)
        self.assertTrue(stale.forward_blocked)
        self.assertTrue(stale.reverse_blocked)
        self.assertIn("stale", stale.reason or "")


if __name__ == "__main__":
    unittest.main()
