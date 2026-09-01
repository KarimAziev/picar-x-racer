import asyncio
import math
import time
import unittest
from typing import Any, List, cast

from app.schemas.autonomy import (
    ActionState,
    MessageHeader,
    Odometry2D,
    RelativeActionType,
    RelativeArcRequest,
    RelativeDistanceRequest,
)
from app.services.autonomy import (
    ActionConflictError,
    IntentSubmissionResult,
    MotionIntent,
    MotionSource,
    RelativeMotionService,
    RobotMode,
    TopicBus,
)
from app.services.autonomy.topics import ODOMETRY


class FakeMotionControl:
    def __init__(self) -> None:
        self.mode = RobotMode.DISARMED
        self.mode_generation = 0
        self.last_result = None
        self.intents: List[MotionIntent] = []
        self.revoked: List[MotionSource] = []

    async def set_mode(self, mode: RobotMode) -> None:
        if mode != self.mode:
            self.mode = mode
            self.mode_generation += 1

    def submit(self, intent: MotionIntent) -> IntentSubmissionResult:
        self.intents.append(intent)
        return IntentSubmissionResult(intent=intent, accepted=True)

    def revoke(self, source: MotionSource) -> None:
        self.revoked.append(source)


def odometry(
    x_m: float,
    *,
    y_m: float = 0,
    yaw_rad: float = 0,
    sequence: int = 1,
    timestamp_ns: int | None = None,
) -> Odometry2D:
    return Odometry2D(
        header=MessageHeader(
            sequence=sequence,
            frame_id="odom",
            timestamp_monotonic_ns=timestamp_ns or time.monotonic_ns(),
        ),
        x_m=x_m,
        y_m=y_m,
        yaw_rad=yaw_rad,
        linear_speed_mps=0,
        yaw_rate_radps=0,
    )


class RelativeMotionServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bus = TopicBus()
        self.motion = FakeMotionControl()
        self.service = RelativeMotionService(
            self.bus,
            cast(Any, self.motion),
            update_period_seconds=0.005,
            odometry_timeout_seconds=0.5,
            wheelbase_m=0.25,
            max_abs_steering_angle_rad=math.radians(30),
        )

    async def asyncTearDown(self) -> None:
        await self.service.stop()

    async def test_completes_forward_distance_and_disarms(self) -> None:
        self.bus.publish(ODOMETRY, odometry(0))
        started = await self.service.start_distance(
            RelativeDistanceRequest(distance_m=0.2, speed_mps=0.1)
        )
        await asyncio.sleep(0.01)

        self.assertEqual(started.state, ActionState.RUNNING)
        self.assertTrue(self.motion.intents)
        self.assertEqual(self.motion.intents[-1].source, MotionSource.AUTONOMY)

        self.bus.publish(ODOMETRY, odometry(0.2))
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.SUCCEEDED)
        self.assertAlmostEqual(self.service.status.progress_m, 0.2)
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)
        self.assertIn(MotionSource.AUTONOMY, self.motion.revoked)

    async def test_completes_arc_with_measured_path_and_yaw(self) -> None:
        distance_m = 0.2
        steering_angle_deg = -20.0
        predicted_yaw = -distance_m / 0.25 * math.tan(math.radians(steering_angle_deg))
        self.bus.publish(ODOMETRY, odometry(0))

        started = await self.service.start_arc(
            RelativeArcRequest(
                distance_m=distance_m,
                speed_mps=0.1,
                steering_angle_deg=steering_angle_deg,
            )
        )
        await asyncio.sleep(0.01)

        self.assertEqual(started.action_type, RelativeActionType.ARC)
        self.assertTrue(self.motion.intents)
        self.assertAlmostEqual(
            self.motion.intents[-1].steering_angle_rad,
            math.radians(steering_angle_deg),
        )

        self.bus.publish(
            ODOMETRY,
            odometry(
                distance_m,
                yaw_rad=predicted_yaw,
                sequence=2,
            ),
        )
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.SUCCEEDED)
        self.assertAlmostEqual(self.service.status.progress_m, distance_m)
        self.assertAlmostEqual(
            self.service.status.yaw_progress_rad or 0,
            predicted_yaw,
        )
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)

    async def test_fails_arc_when_measured_yaw_disagrees(self) -> None:
        self.bus.publish(ODOMETRY, odometry(0))
        await self.service.start_arc(
            RelativeArcRequest(
                distance_m=0.2,
                speed_mps=0.1,
                steering_angle_deg=-20,
            )
        )
        await asyncio.sleep(0.01)

        self.bus.publish(ODOMETRY, odometry(0.2, sequence=2))
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.FAILED)
        self.assertIn("measured yaw", self.service.status.reason or "")
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)

    async def test_reverse_arc_reverses_speed_and_predicted_yaw(self) -> None:
        distance_m = -0.2
        steering_angle_deg = -20.0
        predicted_yaw = -distance_m / 0.25 * math.tan(math.radians(steering_angle_deg))
        self.bus.publish(ODOMETRY, odometry(0))
        await self.service.start_arc(
            RelativeArcRequest(
                distance_m=distance_m,
                speed_mps=0.1,
                steering_angle_deg=steering_angle_deg,
            )
        )
        await asyncio.sleep(0.01)

        self.assertLess(self.motion.intents[-1].linear_speed_mps, 0)
        self.assertAlmostEqual(
            self.service.status.target_yaw_rad or 0,
            predicted_yaw,
        )

        self.bus.publish(
            ODOMETRY,
            odometry(-0.2, yaw_rad=predicted_yaw, sequence=2),
        )
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.SUCCEEDED)

    async def test_arc_fails_safe_when_odometry_becomes_stale(self) -> None:
        self.bus.publish(ODOMETRY, odometry(0))
        await self.service.start_arc(
            RelativeArcRequest(distance_m=0.2, steering_angle_deg=15)
        )
        await asyncio.sleep(0.01)

        self.bus.publish(
            ODOMETRY,
            odometry(
                0.05,
                sequence=2,
                timestamp_ns=time.monotonic_ns() - 1_000_000_000,
            ),
        )
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.FAILED)
        self.assertEqual(self.service.status.reason, "odometry became stale")
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)

    async def test_rejects_arc_outside_configured_steering_range(self) -> None:
        self.bus.publish(ODOMETRY, odometry(0))

        with self.assertRaisesRegex(ActionConflictError, "configured limit"):
            await self.service.start_arc(
                RelativeArcRequest(distance_m=0.2, steering_angle_deg=31)
            )

    async def test_rejects_arc_predicted_to_turn_more_than_half_circle(self) -> None:
        self.bus.publish(ODOMETRY, odometry(0))

        with self.assertRaisesRegex(ActionConflictError, "180 degrees"):
            await self.service.start_arc(
                RelativeArcRequest(distance_m=2, steering_angle_deg=30)
            )

    async def test_cancel_revokes_intent_and_disarms(self) -> None:
        self.bus.publish(ODOMETRY, odometry(0))
        await self.service.start_distance(RelativeDistanceRequest(distance_m=1))
        await asyncio.sleep(0.01)

        status = await self.service.cancel()

        self.assertEqual(status.state, ActionState.CANCELED)
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)

    async def test_manual_takeover_cancels_without_disarming_manual(self) -> None:
        self.bus.publish(ODOMETRY, odometry(0))
        await self.service.start_distance(RelativeDistanceRequest(distance_m=1))
        await asyncio.sleep(0.01)
        await self.motion.set_mode(RobotMode.MANUAL)
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.CANCELED)
        self.assertEqual(self.motion.mode, RobotMode.MANUAL)

    async def test_rejects_start_without_fresh_odometry(self) -> None:
        self.bus.publish(
            ODOMETRY,
            odometry(0, timestamp_ns=time.monotonic_ns() - 1_000_000_000),
        )

        with self.assertRaisesRegex(ActionConflictError, "fresh odometry"):
            await self.service.start_distance(RelativeDistanceRequest(distance_m=1))


if __name__ == "__main__":
    unittest.main()
