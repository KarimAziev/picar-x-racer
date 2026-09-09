import asyncio
import time
import unittest
from unittest.mock import AsyncMock
from typing import Any, List, cast

from pydantic import ValidationError

from app.schemas.autonomy import (
    ActionState,
    LocalizationPose2D,
    MessageHeader,
    NavigationDirection,
    NavigationExecutionRequest,
    NavigationExecutionStatus,
    NavigationGoalRequest,
    NavigationMissionExecutionRequest,
    NavigationMissionMode,
    NavigationMissionReviewRequest,
    NavigationMissionTarget,
    NavigationPlanState,
    NavigationPlanStatus,
    NavigationPoint,
    OccupancyGrid,
)
from app.services.autonomy import NavigationMissionService, TopicBus
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP, MISSION_STATUS


def header(sequence: int = 1) -> MessageHeader:
    return MessageHeader(
        sequence=sequence,
        frame_id="odom",
        timestamp_monotonic_ns=time.monotonic_ns(),
    )


def pose(x_m: float, y_m: float, sequence: int = 1) -> LocalizationPose2D:
    return LocalizationPose2D(
        header=header(sequence),
        x_m=x_m,
        y_m=y_m,
        yaw_rad=0.0,
        linear_speed_mps=0.0,
        yaw_rate_radps=0.0,
        position_variance_m2=0.001,
        yaw_variance_rad2=0.001,
        fusion_mode="corrected",
    )


def grid(sequence: int = 7) -> OccupancyGrid:
    return OccupancyGrid(
        header=header(sequence),
        width=50,
        height=50,
        resolution_m=0.1,
        origin_x_m=-1.0,
        origin_y_m=-1.0,
        origin_yaw_rad=0.0,
        data=tuple([0] * 2500),
    )


class FakePlanningService:
    def __init__(self, bus: TopicBus) -> None:
        self.bus = bus
        self.status = NavigationPlanStatus.idle()
        self.preflight_starts: List[NavigationPoint] = []
        self.live_starts: List[NavigationPoint] = []

    async def preview_from_pose(
        self,
        request: NavigationGoalRequest,
        *,
        grid: OccupancyGrid,
        start_x_m: float,
        start_y_m: float,
        start_yaw_rad: float,
    ) -> NavigationPlanStatus:
        del start_yaw_rad
        start = NavigationPoint(x_m=start_x_m, y_m=start_y_m)
        self.preflight_starts.append(start)
        return self._ready(request, grid, start)

    async def plan(self, request: NavigationGoalRequest) -> NavigationPlanStatus:
        current = self.bus.latest(LOCALIZATION_POSE)
        current_grid = self.bus.latest(LOCAL_MAP)
        assert current is not None and current_grid is not None
        start = NavigationPoint(x_m=current.x_m, y_m=current.y_m)
        self.live_starts.append(start)
        self.status = self._ready(request, current_grid, start)
        return self.status

    async def clear(self) -> NavigationPlanStatus:
        self.status = NavigationPlanStatus.idle()
        return self.status

    @staticmethod
    def _ready(
        request: NavigationGoalRequest,
        grid: OccupancyGrid,
        start: NavigationPoint,
    ) -> NavigationPlanStatus:
        goal = NavigationPoint(x_m=request.x_m, y_m=request.y_m)
        length = ((goal.x_m - start.x_m) ** 2 + (goal.y_m - start.y_m) ** 2) ** 0.5
        return NavigationPlanStatus(
            available=True,
            state=NavigationPlanState.READY,
            frame_id=grid.header.frame_id,
            goal=goal,
            start=start,
            path=(start, goal),
            path_directions=(NavigationDirection.FORWARD,),
            path_length_m=length,
            clearance_m=request.clearance_m,
            allow_unknown=request.allow_unknown,
            map_sequence=grid.header.sequence,
            pose_source="localization",
            start_yaw_rad=0.0,
            geometry_validated=True,
        )


class ImmediateExecutionService:
    def __init__(self, bus: TopicBus, planning: FakePlanningService) -> None:
        self.bus = bus
        self.planning = planning
        self.status = NavigationExecutionStatus.idle()
        self.starts: List[NavigationExecutionRequest] = []

    @property
    def running(self) -> bool:
        return False

    async def start(
        self, request: NavigationExecutionRequest
    ) -> NavigationExecutionStatus:
        self.starts.append(request)
        plan = self.planning.status
        assert plan.goal is not None
        self.bus.publish(
            LOCALIZATION_POSE,
            pose(plan.goal.x_m, plan.goal.y_m, sequence=len(self.starts) + 1),
        )
        self.status = NavigationExecutionStatus(
            available=True,
            state=ActionState.SUCCEEDED,
            action_id=f"leg-{len(self.starts)}",
            goal=plan.goal,
            current_pose=plan.goal,
            map_sequence=plan.map_sequence,
            path_length_m=plan.path_length_m,
            progress_m=plan.path_length_m,
            remaining_m=0.0,
            reason="navigation goal reached",
        )
        return self.status

    async def pause(self) -> NavigationExecutionStatus:
        return self.status

    async def resume(self) -> NavigationExecutionStatus:
        return self.status

    async def cancel(
        self, reason: str = "operator canceled"
    ) -> NavigationExecutionStatus:
        self.status = self.status.model_copy(
            update={"state": ActionState.CANCELED, "reason": reason}
        )
        return self.status


class HoldingExecutionService(ImmediateExecutionService):
    def __init__(self, bus: TopicBus, planning: FakePlanningService) -> None:
        super().__init__(bus, planning)
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def start(
        self, request: NavigationExecutionRequest
    ) -> NavigationExecutionStatus:
        self.starts.append(request)
        plan = self.planning.status
        self._running = True
        self.status = NavigationExecutionStatus(
            available=True,
            state=ActionState.RUNNING,
            action_id="held-leg",
            goal=plan.goal,
            current_pose=plan.start,
            map_sequence=plan.map_sequence,
            path_length_m=plan.path_length_m,
            remaining_m=plan.path_length_m,
            reason="following",
        )
        return self.status

    async def pause(self) -> NavigationExecutionStatus:
        self.status = self.status.model_copy(update={"state": ActionState.PAUSED})
        return self.status

    async def resume(self) -> NavigationExecutionStatus:
        self.status = self.status.model_copy(update={"state": ActionState.RUNNING})
        return self.status

    async def cancel(
        self, reason: str = "operator canceled"
    ) -> NavigationExecutionStatus:
        self._running = False
        return await super().cancel(reason)


class NavigationMissionSchemaTests(unittest.TestCase):
    def test_loop_requires_two_distinct_targets(self) -> None:
        with self.assertRaises(ValidationError):
            NavigationMissionReviewRequest(
                targets=(NavigationMissionTarget(x_m=1, y_m=1),),
                mode=NavigationMissionMode.LOOP,
            )
        with self.assertRaises(ValidationError):
            NavigationMissionReviewRequest(
                targets=(
                    NavigationMissionTarget(x_m=1, y_m=1),
                    NavigationMissionTarget(x_m=1.005, y_m=1),
                ),
                mode=NavigationMissionMode.LOOP,
            )


class NavigationMissionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.bus = TopicBus()
        self.bus.publish(LOCAL_MAP, grid())
        self.bus.publish(LOCALIZATION_POSE, pose(0, 0))
        self.planning = FakePlanningService(self.bus)
        self.execution = ImmediateExecutionService(self.bus, self.planning)
        self.service = NavigationMissionService(
            self.bus,
            cast(Any, self.planning),
            cast(Any, self.execution),
            update_period_seconds=0.001,
        )

    async def asyncTearDown(self) -> None:
        await self.service.stop()

    async def test_cancel_during_planning_never_starts_a_leg_and_clears_route(
        self,
    ) -> None:
        await self.service.review(
            NavigationMissionReviewRequest(
                targets=(NavigationMissionTarget(x_m=1, y_m=0),),
            )
        )
        planning_started = asyncio.Event()

        async def slow_plan(request: NavigationGoalRequest) -> NavigationPlanStatus:
            planning_started.set()
            await asyncio.Event().wait()
            raise AssertionError("canceled planning must not finish")

        self.planning.plan = AsyncMock(side_effect=slow_plan)
        await self.service.start(NavigationMissionExecutionRequest())
        await asyncio.wait_for(planning_started.wait(), 1)
        await self.service.cancel()
        self.assertEqual(self.execution.starts, [])
        self.assertEqual(self.planning.status.state, NavigationPlanState.IDLE)
        self.assertEqual(self.service.status.state, ActionState.CANCELED)
        self.assertEqual(self.bus.latest(MISSION_STATUS), self.service.status)

    async def test_pause_during_planning_holds_start_until_resume(self) -> None:
        await self.service.review(
            NavigationMissionReviewRequest(
                targets=(NavigationMissionTarget(x_m=1, y_m=0),),
            )
        )
        planning_started = asyncio.Event()
        finish_planning = asyncio.Event()
        planned = asyncio.Event()
        original = self.planning.plan

        async def slow_plan(request: NavigationGoalRequest) -> NavigationPlanStatus:
            planning_started.set()
            await finish_planning.wait()
            result = await original(request)
            planned.set()
            return result

        self.planning.plan = AsyncMock(side_effect=slow_plan)
        await self.service.start(NavigationMissionExecutionRequest())
        await asyncio.wait_for(planning_started.wait(), 1)
        await self.service.pause()
        finish_planning.set()
        await asyncio.wait_for(planned.wait(), 1)
        self.assertEqual(self.execution.starts, [])
        self.assertEqual(self.service.status.state, ActionState.PAUSED)
        await self.service.resume()
        for _ in range(20):
            if not self.service.running:
                break
            await asyncio.sleep(0.001)
        self.assertEqual(len(self.execution.starts), 1)
        self.assertEqual(self.service.status.state, ActionState.SUCCEEDED)

    async def test_live_planner_failure_is_terminal_without_motion(self) -> None:
        await self.service.review(
            NavigationMissionReviewRequest(
                targets=(NavigationMissionTarget(x_m=1, y_m=0),),
            )
        )
        self.planning.plan = AsyncMock(side_effect=ValueError("test route rejected"))
        await self.service.start(NavigationMissionExecutionRequest())
        for _ in range(20):
            if not self.service.running:
                break
            await asyncio.sleep(0.001)
        self.assertEqual(self.execution.starts, [])
        self.assertEqual(self.service.status.state, ActionState.FAILED)
        self.assertIn("test route rejected", self.service.status.reason or "")
        self.assertEqual(self.planning.status.state, NavigationPlanState.IDLE)

    async def test_loop_preflight_includes_closure_and_scales_lap_distance(
        self,
    ) -> None:
        reviewed = await self.service.review(
            NavigationMissionReviewRequest(
                targets=(
                    NavigationMissionTarget(x_m=1, y_m=0),
                    NavigationMissionTarget(x_m=2, y_m=0),
                ),
                mode=NavigationMissionMode.LOOP,
                lap_count=2,
                clearance_m=0,
            )
        )

        self.assertEqual(reviewed.state, NavigationPlanState.READY)
        self.assertEqual(len(reviewed.legs), 3)
        self.assertEqual(
            [(leg.from_target_index, leg.to_target_index) for leg in reviewed.legs],
            [(None, 0), (0, 1), (1, 0)],
        )
        self.assertAlmostEqual(reviewed.total_path_length_m, 5.0)
        self.assertEqual(
            self.planning.preflight_starts,
            [
                NavigationPoint(x_m=0, y_m=0),
                NavigationPoint(x_m=1, y_m=0),
                NavigationPoint(x_m=2, y_m=0),
            ],
        )

    async def test_execution_replans_every_leg_from_latest_fused_pose(self) -> None:
        await self.service.review(
            NavigationMissionReviewRequest(
                targets=(
                    NavigationMissionTarget(x_m=1, y_m=0),
                    NavigationMissionTarget(x_m=2, y_m=0),
                ),
                mode=NavigationMissionMode.LOOP,
                lap_count=1,
                clearance_m=0,
            )
        )

        started = await self.service.start(NavigationMissionExecutionRequest())
        self.assertEqual(started.state, ActionState.RUNNING)
        for _ in range(20):
            if not self.service.running:
                break
            await asyncio.sleep(0.002)

        self.assertEqual(self.service.status.state, ActionState.SUCCEEDED)
        self.assertEqual(self.service.status.completed_target_visits, 3)
        self.assertEqual(self.service.status.total_target_visits, 3)
        self.assertEqual(
            self.planning.live_starts,
            [
                NavigationPoint(x_m=0, y_m=0),
                NavigationPoint(x_m=1, y_m=0),
                NavigationPoint(x_m=2, y_m=0),
            ],
        )

    async def test_execution_blocks_when_reviewed_map_changes(self) -> None:
        await self.service.review(
            NavigationMissionReviewRequest(
                targets=(NavigationMissionTarget(x_m=1, y_m=0),),
                clearance_m=0,
            )
        )
        self.bus.publish(LOCAL_MAP, grid(sequence=8))

        with self.assertRaisesRegex(Exception, "map changed"):
            await self.service.start(NavigationMissionExecutionRequest())

    async def test_disabled_execution_still_allows_preflight(self) -> None:
        service = NavigationMissionService(
            self.bus,
            cast(Any, self.planning),
            None,
        )

        reviewed = await service.review(
            NavigationMissionReviewRequest(
                targets=(NavigationMissionTarget(x_m=1, y_m=0),),
                clearance_m=0,
            )
        )

        self.assertEqual(reviewed.state, NavigationPlanState.READY)
        self.assertFalse(service.status.available)

    async def test_pauses_resumes_and_cancels_the_active_live_leg(self) -> None:
        execution = HoldingExecutionService(self.bus, self.planning)
        service = NavigationMissionService(
            self.bus,
            cast(Any, self.planning),
            cast(Any, execution),
            update_period_seconds=0.001,
        )
        await service.review(
            NavigationMissionReviewRequest(
                targets=(NavigationMissionTarget(x_m=1, y_m=0),),
                clearance_m=0,
            )
        )
        await service.start(NavigationMissionExecutionRequest())
        for _ in range(20):
            if execution.running:
                break
            await asyncio.sleep(0.001)

        paused = await service.pause()
        resumed = await service.resume()
        canceled = await service.cancel()

        self.assertEqual(paused.state, ActionState.PAUSED)
        self.assertEqual(resumed.state, ActionState.RUNNING)
        self.assertEqual(canceled.state, ActionState.CANCELED)
        self.assertFalse(execution.running)


if __name__ == "__main__":
    unittest.main()
