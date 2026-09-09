"""Replay fixed-step simulated pose streams into the real navigation executor."""

import asyncio
import math
import unittest
from typing import cast

from app.schemas.autonomy import (
    ActionState,
    NavigationExecutionRequest,
    NavigationGoalRequest,
)
from app.services.autonomy import (
    AckermannPathSmoother,
    MotionArbiter,
    MotionLimits,
    NavigationExecutionService,
    NavigationPlanningService,
    OccupancyGridPlanner,
    RobotMode,
    TopicBus,
)
from app.services.autonomy.clock import ReplayClock
from app.services.autonomy.messages import (
    MotionIntent,
    MotionSource,
    IntentSubmissionResult,
)
from app.services.autonomy.motion_control_service import MotionControlService
from app.services.autonomy.topics import (
    ENCODER_STATE,
    IMU_DATA,
    LOCALIZATION_POSE,
    LOCAL_MAP,
)
from tests.services.autonomy.fault_scenarios import DeliveryFault, advance_step
from tests.services.autonomy.test_navigation_execution import FakeMotionControl
from tests.services.autonomy.test_navigation_mission import grid
from tests.services.autonomy.test_sensor_fault_scenarios import DriveReport, drive


class ArbitratedMotion(FakeMotionControl):
    """No hardware; use the real arbiter to verify revocation and zero output."""

    def __init__(self, clock: ReplayClock) -> None:
        super().__init__()
        self.arbiter = MotionArbiter(
            MotionLimits(
                max_forward_speed_mps=1,
                max_reverse_speed_mps=0.5,
                max_abs_steering_angle_rad=0.6,
            ),
            clock,
        )

    def submit(self, intent: MotionIntent) -> IntentSubmissionResult:
        self.intents.append(intent)
        return self.arbiter.submit(
            intent, mode=self.mode, mode_generation=self.mode_generation
        )

    def revoke(self, source: MotionSource) -> None:
        super().revoke(source)
        self.arbiter.revoke(source)

    def resolve(self) -> float:
        self.last_result = self.arbiter.resolve(
            mode=self.mode, mode_generation=self.mode_generation
        )
        return self.last_result.command.linear_speed_mps


class NavigationFaultScenarios(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.clock = ReplayClock()
        advance_step(self.clock, 0)
        self.bus = TopicBus()
        self.motion = ArbitratedMotion(self.clock)
        self.planning = NavigationPlanningService(
            self.bus,
            OccupancyGridPlanner(
                path_smoother=AckermannPathSmoother(
                    wheelbase_m=0.25,
                    max_abs_steering_angle_rad=math.radians(30),
                )
            ),
            clock=self.clock,
        )
        self.execution = NavigationExecutionService(
            self.bus,
            cast(MotionControlService, self.motion),
            self.planning,
            wheelbase_m=0.25,
            max_abs_steering_angle_rad=math.radians(30),
            clock=self.clock,
            update_period_seconds=0,
        )

    async def asyncTearDown(self) -> None:
        await self.execution.stop()
        self.bus.close()

    async def play(self, report: DriveReport) -> tuple[int | None, tuple[float, ...]]:
        self.bus.publish(LOCAL_MAP, grid())
        self.bus.publish(LOCALIZATION_POSE, report.poses[0])
        await self.planning.plan(NavigationGoalRequest(x_m=0.5, y_m=0, clearance_m=0))
        await self.execution.start(NavigationExecutionRequest())
        first_failure = None
        speeds = []
        by_timestamp = {
            pose.header.timestamp_monotonic_ns: pose for pose in report.poses
        }
        for step in range(151):
            timestamp = advance_step(self.clock, step)
            pose = by_timestamp.get(timestamp)
            if pose is not None:
                self.bus.publish(LOCALIZATION_POSE, pose)
            # Zero-duration yields let the real execution task run. Virtual time
            # advances only above; no wall-clock sleep sets the scenario outcome.
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            speeds.append(self.motion.resolve())
            if (
                first_failure is None
                and self.execution.status.state == ActionState.FAILED
            ):
                first_failure = step
        return first_failure, tuple(speeds)

    async def test_imu_dropout_does_not_abort_navigation(self) -> None:
        report = await drive((DeliveryFault(IMU_DATA.name, 30, 70, drop=True),))
        failed, speeds = await self.play(report)
        self.assertIsNone(failed)
        self.assertIn("wheel", {pose.fusion_mode for pose in report.poses})
        self.assertEqual(self.execution.status.state, ActionState.SUCCEEDED)
        self.assertGreater(max(speeds), 0)
        self.assertEqual(speeds[-1], 0)
        self.assertIsNone(self.motion.autonomy_owner)

    async def test_healthy_drive_reaches_goal(self) -> None:
        failed, _ = await self.play(await drive())
        self.assertIsNone(failed)
        self.assertEqual(self.execution.status.state, ActionState.SUCCEEDED)

    async def test_encoder_outage_fails_within_pose_timeout_and_never_auto_resumes(
        self,
    ) -> None:
        report = await drive((DeliveryFault(ENCODER_STATE.name, 30, 70, drop=True),))
        failed, speeds = await self.play(report)
        self.assertEqual(failed, 55)  # Last pose at step 29; 26 * 20 ms > 500 ms.
        self.assertTrue(all(speed == 0 for speed in speeds[55:]))
        self.assertEqual(self.execution.status.state, ActionState.FAILED)
        self.assertIn("stale", self.execution.status.reason or "")
        self.assertEqual(self.motion.mode, RobotMode.DISARMED)
        self.assertIsNone(self.motion.autonomy_owner)
        self.assertIn(MotionSource.AUTONOMY, self.motion.revoked)
        # Sensor recovery is not authorization to resume. A new reviewed start is.
        await self.planning.plan(NavigationGoalRequest(x_m=1.0, y_m=0, clearance_m=0))
        await self.execution.start(NavigationExecutionRequest())
        await asyncio.sleep(0)
        self.assertEqual(self.execution.status.state, ActionState.RUNNING)
        self.assertGreater(self.motion.resolve(), 0)

    async def test_short_encoder_gap_does_not_abort_navigation(self) -> None:
        failed, _ = await self.play(
            await drive((DeliveryFault(ENCODER_STATE.name, 30, 35, drop=True),))
        )
        self.assertIsNone(failed)
        self.assertEqual(self.execution.status.state, ActionState.SUCCEEDED)
