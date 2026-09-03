import asyncio
import math
import time
import unittest
from typing import Any, List, cast

from app.schemas.autonomy import (
    ActionState,
    LocalizationPose2D,
    MessageHeader,
    NavigationExecutionRequest,
    NavigationGoalRequest,
    NavigationPoint,
    OccupancyGrid,
)
from app.services.autonomy import (
    ActuatorCommand,
    ActionConflictError,
    ArbitrationResult,
    IntentSubmissionResult,
    MotionIntent,
    MotionSource,
    NavigationExecutionService,
    NavigationPlanningService,
    PurePursuitTracker,
    RobotMode,
    TopicBus,
)
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP


class FakeMotionControl:
    def __init__(self) -> None:
        self.mode = RobotMode.DISARMED
        self.mode_generation = 0
        self.last_result: ArbitrationResult | None = None
        self.intents: List[MotionIntent] = []
        self.revoked: List[MotionSource] = []
        self.autonomy_owner: str | None = None

    async def set_mode(self, mode: RobotMode) -> None:
        if mode != self.mode:
            self.mode = mode
            self.mode_generation += 1

    def submit(self, intent: MotionIntent) -> IntentSubmissionResult:
        self.intents.append(intent)
        return IntentSubmissionResult(intent=intent, accepted=True)

    def revoke(self, source: MotionSource) -> None:
        self.revoked.append(source)

    def claim_autonomy(self, owner: str) -> bool:
        if self.autonomy_owner not in {None, owner}:
            return False
        self.autonomy_owner = owner
        return True

    def release_autonomy(self, owner: str) -> None:
        if self.autonomy_owner == owner:
            self.autonomy_owner = None


def header(sequence: int = 1) -> MessageHeader:
    return MessageHeader(
        sequence=sequence,
        frame_id="odom",
        timestamp_monotonic_ns=time.monotonic_ns(),
    )


def pose(
    x_m: float,
    y_m: float,
    *,
    yaw_rad: float = 0.0,
    sequence: int = 1,
    timestamp_ns: int | None = None,
) -> LocalizationPose2D:
    return LocalizationPose2D(
        header=MessageHeader(
            sequence=sequence,
            frame_id="odom",
            timestamp_monotonic_ns=timestamp_ns or time.monotonic_ns(),
        ),
        x_m=x_m,
        y_m=y_m,
        yaw_rad=yaw_rad,
        linear_speed_mps=0.0,
        yaw_rate_radps=0.0,
        position_variance_m2=0.001,
        yaw_variance_rad2=0.001,
        fusion_mode="corrected",
    )


def occupancy_grid(sequence: int = 7) -> OccupancyGrid:
    return OccupancyGrid(
        header=header(sequence),
        width=30,
        height=20,
        resolution_m=0.1,
        origin_x_m=0.0,
        origin_y_m=0.0,
        origin_yaw_rad=0.0,
        data=tuple([0] * 600),
    )


class PurePursuitTrackerTests(unittest.TestCase):
    def test_uses_project_steering_sign_convention(self) -> None:
        left = PurePursuitTracker(
            (NavigationPoint(x_m=0, y_m=0), NavigationPoint(x_m=1, y_m=1)),
            wheelbase_m=0.25,
            max_abs_steering_angle_rad=math.radians(30),
            lookahead_m=0.25,
        ).update(pose(0, 0))
        right = PurePursuitTracker(
            (NavigationPoint(x_m=0, y_m=0), NavigationPoint(x_m=1, y_m=-1)),
            wheelbase_m=0.25,
            max_abs_steering_angle_rad=math.radians(30),
            lookahead_m=0.25,
        ).update(pose(0, 0))

        self.assertLess(left.steering_angle_rad, 0)
        self.assertGreater(right.steering_angle_rad, 0)

    def test_progress_is_monotonic_when_pose_moves_backwards(self) -> None:
        tracker = PurePursuitTracker(
            (NavigationPoint(x_m=0, y_m=0), NavigationPoint(x_m=2, y_m=0)),
            wheelbase_m=0.25,
            max_abs_steering_angle_rad=math.radians(30),
            lookahead_m=0.25,
        )

        first = tracker.update(pose(1, 0))
        second = tracker.update(pose(0.5, 0))

        self.assertEqual(first.progress_m, 1.0)
        self.assertEqual(second.progress_m, 1.0)


class NavigationExecutionServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bus = TopicBus()
        self.motion = FakeMotionControl()
        self.planning = NavigationPlanningService(self.bus)
        self.service = NavigationExecutionService(
            self.bus,
            cast(Any, self.motion),
            self.planning,
            wheelbase_m=0.25,
            max_abs_steering_angle_rad=math.radians(30),
            update_period_seconds=0.005,
            localization_timeout_seconds=0.5,
        )

    async def asyncTearDown(self) -> None:
        await self.service.stop()

    async def prepare_route(self) -> None:
        self.bus.publish(LOCAL_MAP, occupancy_grid())
        self.bus.publish(LOCALIZATION_POSE, pose(0.5, 0.5))
        await self.planning.plan(
            NavigationGoalRequest(
                x_m=1.5,
                y_m=0.5,
                clearance_m=0.0,
            )
        )

    async def test_follows_route_to_goal_and_releases_autonomy(self) -> None:
        await self.prepare_route()

        started = await self.service.start(NavigationExecutionRequest())
        await asyncio.sleep(0.015)

        self.assertEqual(started.state, ActionState.RUNNING)
        self.assertTrue(self.motion.intents)
        self.assertGreater(self.motion.intents[-1].linear_speed_mps, 0)
        self.assertEqual(self.motion.mode, RobotMode.AUTONOMOUS)

        self.bus.publish(LOCALIZATION_POSE, pose(1.5, 0.5, sequence=2))
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.SUCCEEDED)
        self.assertEqual(
            self.service.status.progress_m, self.service.status.path_length_m
        )
        self.assertEqual(self.service.status.remaining_m, 0.0)
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)
        self.assertIsNone(self.motion.autonomy_owner)

    async def test_pauses_resumes_and_cancels_safely(self) -> None:
        await self.prepare_route()
        await self.service.start(NavigationExecutionRequest())
        await asyncio.sleep(0.01)

        paused = await self.service.pause()
        self.assertEqual(paused.state, ActionState.PAUSED)
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)
        self.assertIsNotNone(self.motion.autonomy_owner)

        resumed = await self.service.resume()
        self.assertEqual(resumed.state, ActionState.RUNNING)
        self.assertEqual(self.motion.mode, RobotMode.AUTONOMOUS)

        canceled = await self.service.cancel()
        self.assertEqual(canceled.state, ActionState.CANCELED)
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)
        self.assertIsNone(self.motion.autonomy_owner)

    async def test_blocks_when_map_snapshot_changes(self) -> None:
        await self.prepare_route()
        await self.service.start(NavigationExecutionRequest())
        await asyncio.sleep(0.01)

        self.bus.publish(LOCAL_MAP, occupancy_grid(sequence=8))
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.BLOCKED)
        self.assertIn("map changed", self.service.status.reason or "")
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)

    async def test_resume_preserves_blocked_reason_when_map_changed(self) -> None:
        await self.prepare_route()
        await self.service.start(NavigationExecutionRequest())
        await self.service.pause()
        self.bus.publish(LOCAL_MAP, occupancy_grid(sequence=8))

        resumed = await self.service.resume()
        await asyncio.sleep(0.01)

        self.assertEqual(resumed.state, ActionState.BLOCKED)
        self.assertEqual(self.service.status.state, ActionState.BLOCKED)
        self.assertEqual(
            self.service.status.reason, "route or map changed while paused"
        )

    async def test_manual_takeover_cancels_a_paused_navigation(self) -> None:
        await self.prepare_route()
        await self.service.start(NavigationExecutionRequest())
        await self.service.pause()

        await self.motion.set_mode(RobotMode.MANUAL)
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.CANCELED)
        self.assertEqual(self.motion.mode, RobotMode.MANUAL)
        self.assertIsNone(self.motion.autonomy_owner)

    async def test_fails_when_localization_becomes_stale(self) -> None:
        await self.prepare_route()
        await self.service.start(NavigationExecutionRequest())
        await asyncio.sleep(0.01)
        self.bus.publish(
            LOCALIZATION_POSE,
            pose(
                0.6,
                0.5,
                sequence=2,
                timestamp_ns=time.monotonic_ns() - 1_000_000_000,
            ),
        )
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.FAILED)
        self.assertEqual(self.service.status.reason, "localization became stale")

    async def test_reports_arbiter_safety_stop_as_blocked(self) -> None:
        await self.prepare_route()
        await self.service.start(NavigationExecutionRequest())
        await asyncio.sleep(0.01)
        selected = self.motion.intents[-1]
        self.motion.last_result = ArbitrationResult(
            command=ActuatorCommand(
                source=MotionSource.SAFETY,
                linear_speed_mps=0.0,
                steering_angle_rad=0.0,
                selected_monotonic_ns=time.monotonic_ns(),
                command_id=selected.command_id,
                reason="forward obstacle inside stop zone",
            ),
            selected_intent=selected,
        )
        await asyncio.sleep(0.02)

        self.assertEqual(self.service.status.state, ActionState.BLOCKED)
        self.assertEqual(
            self.service.status.reason, "forward obstacle inside stop zone"
        )
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)

    async def test_rejects_start_when_autonomy_source_is_owned(self) -> None:
        await self.prepare_route()
        self.motion.autonomy_owner = "relative-motion:other"

        with self.assertRaisesRegex(ActionConflictError, "another autonomous"):
            await self.service.start(NavigationExecutionRequest())


if __name__ == "__main__":
    unittest.main()
