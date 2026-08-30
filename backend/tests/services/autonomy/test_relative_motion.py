import asyncio
import time
import unittest
from typing import Any, List, cast

from app.schemas.autonomy import (
    ActionState,
    MessageHeader,
    Odometry2D,
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


def odometry(x_m: float, *, timestamp_ns: int | None = None) -> Odometry2D:
    return Odometry2D(
        header=MessageHeader(
            sequence=1,
            frame_id="odom",
            timestamp_monotonic_ns=timestamp_ns or time.monotonic_ns(),
        ),
        x_m=x_m,
        y_m=0,
        yaw_rad=0,
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
