"""Review and execute ordered navigation targets using fresh poses per leg."""

import asyncio
import math
import time
import uuid
from typing import Optional

from app.schemas.autonomy import (
    ActionState,
    LocalizationPose2D,
    NavigationDirection,
    NavigationExecutionRequest,
    NavigationGoalRequest,
    NavigationMissionExecutionRequest,
    NavigationMissionExecutionStatus,
    NavigationMissionLeg,
    NavigationMissionMode,
    NavigationMissionPlanStatus,
    NavigationMissionReviewRequest,
    NavigationMissionTarget,
    NavigationPlanState,
    NavigationPlanStatus,
    OccupancyGrid,
)
from app.services.autonomy.navigation_execution import NavigationExecutionService
from app.services.autonomy.navigation_planning import (
    NavigationPlanRejected,
    NavigationPlanningService,
)
from app.services.autonomy.relative_motion import ActionConflictError
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP


class NavigationMissionService:
    """Preflight a mission, then replan every leg from fresh fused localization."""

    def __init__(
        self,
        bus: TopicBus,
        planning: NavigationPlanningService,
        execution: Optional[NavigationExecutionService],
        *,
        localization_timeout_seconds: float = 0.5,
        update_period_seconds: float = 0.02,
    ) -> None:
        if localization_timeout_seconds <= 0 or update_period_seconds <= 0:
            raise ValueError("mission timing limits must be positive")
        self._bus = bus
        self._planning = planning
        self._execution = execution
        self._localization_timeout_ns = int(localization_timeout_seconds * 1e9)
        self._update_period_seconds = update_period_seconds
        self._plan = NavigationMissionPlanStatus.idle()
        self._status = (
            NavigationMissionExecutionStatus.idle()
            if execution is not None
            else NavigationMissionExecutionStatus.unavailable()
        )
        self._task: Optional[asyncio.Task[None]] = None
        self._pause_gate = asyncio.Event()
        self._pause_gate.set()
        self._lock = asyncio.Lock()

    @property
    def plan_status(self) -> NavigationMissionPlanStatus:
        return self._plan

    @property
    def status(self) -> NavigationMissionExecutionStatus:
        return self._status

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def review(
        self, request: NavigationMissionReviewRequest
    ) -> NavigationMissionPlanStatus:
        """Validate the entry route and every target-to-target route without motion."""

        async with self._lock:
            if self.running:
                raise ActionConflictError(
                    "cancel the active mission before reviewing it"
                )
            self._reset_execution_status()
            await self._planning.clear()
            grid = self._bus.latest(LOCAL_MAP)
            if grid is None:
                return self._reject_review(request, "no occupancy map is available")
            pose = self._fresh_localization(grid.header.frame_id)
            if pose is None:
                return self._reject_review(
                    request,
                    "fresh fused localization is required to review a mission",
                    grid=grid,
                )
            legs = []
            start_x_m = pose.x_m
            start_y_m = pose.y_m
            start_yaw_rad = pose.yaw_rad
            from_target_index: Optional[int] = None
            target_indices = list(range(len(request.targets)))
            if request.mode == NavigationMissionMode.LOOP:
                target_indices.append(0)
            leg_number = 0
            try:
                for leg_number, target_index in enumerate(target_indices):
                    target = request.targets[target_index]
                    if (
                        math.hypot(target.x_m - start_x_m, target.y_m - start_y_m)
                        < 0.01
                    ):
                        from_target_index = target_index
                        continue
                    plan = await self._planning.preview_from_pose(
                        self._goal_request(request, target),
                        grid=grid,
                        start_x_m=start_x_m,
                        start_y_m=start_y_m,
                        start_yaw_rad=start_yaw_rad,
                    )
                    if not plan.geometry_validated:
                        raise NavigationPlanRejected(
                            "mission routes require configured Ackermann geometry"
                        )
                    legs.append(
                        NavigationMissionLeg(
                            from_target_index=from_target_index,
                            to_target_index=target_index,
                            plan=plan,
                        )
                    )
                    start_x_m = target.x_m
                    start_y_m = target.y_m
                    start_yaw_rad = self._terminal_vehicle_yaw(
                        plan, fallback=start_yaw_rad
                    )
                    from_target_index = target_index
            except NavigationPlanRejected as error:
                return self._reject_review(
                    request,
                    f"leg {leg_number + 1} cannot be validated: {error}",
                    grid=grid,
                )
            except Exception as error:
                return self._fail_review(
                    request, f"mission planner failed: {error}", grid
                )

            current_grid = self._bus.latest(LOCAL_MAP)
            if not self._same_map(current_grid, grid):
                return self._reject_review(
                    request,
                    "the occupancy map changed while the mission was being reviewed",
                    grid=grid,
                )
            one_pass_distance = sum(leg.plan.path_length_m for leg in legs)
            loop_distance = 0.0
            if request.mode == NavigationMissionMode.LOOP:
                loop_distance = sum(
                    leg.plan.path_length_m
                    for leg in legs
                    if leg.from_target_index is not None
                )
                entry_distance = one_pass_distance - loop_distance
                total_distance = entry_distance + loop_distance * request.lap_count
            else:
                total_distance = one_pass_distance
            reverse_distance = sum(leg.plan.reverse_distance_m for leg in legs)
            if request.mode == NavigationMissionMode.LOOP:
                loop_reverse = sum(
                    leg.plan.reverse_distance_m
                    for leg in legs
                    if leg.from_target_index is not None
                )
                entry_reverse = reverse_distance - loop_reverse
                reverse_distance = entry_reverse + loop_reverse * request.lap_count
            self._plan = NavigationMissionPlanStatus(
                available=True,
                state=NavigationPlanState.READY,
                frame_id=grid.header.frame_id,
                mode=request.mode,
                lap_count=request.lap_count,
                targets=request.targets,
                legs=tuple(legs),
                map_sequence=grid.header.sequence,
                total_path_length_m=total_distance,
                total_reverse_distance_m=reverse_distance,
                reason=(
                    f"Validated {len(legs)} route legs; each live leg will be "
                    "replanned from fresh fused localization"
                ),
            )
            return self._plan

    async def clear(self) -> NavigationMissionPlanStatus:
        async with self._lock:
            if self.running:
                raise ActionConflictError(
                    "cancel the active mission before clearing it"
                )
            self._plan = NavigationMissionPlanStatus.idle()
            self._reset_execution_status()
            await self._planning.clear()
            return self._plan

    async def start(
        self, request: NavigationMissionExecutionRequest
    ) -> NavigationMissionExecutionStatus:
        async with self._lock:
            if self._execution is None:
                raise ActionConflictError(
                    self._status.reason or "mission is unavailable"
                )
            if self.running:
                raise ActionConflictError("a navigation mission is already running")
            if self._plan.state != NavigationPlanState.READY or not self._plan.targets:
                raise ActionConflictError("a reviewed mission is required")
            grid = self._bus.latest(LOCAL_MAP)
            if (
                grid is None
                or self._plan.map_sequence is None
                or not self._same_map_sequence(grid, self._plan.map_sequence)
            ):
                raise ActionConflictError(
                    "the occupancy map changed; review the mission again"
                )
            if self._fresh_localization(self._plan.frame_id) is None:
                raise ActionConflictError("fresh fused localization is required")
            mission_id = uuid.uuid4().hex
            total_visits = (
                len(self._plan.targets)
                if self._plan.mode == NavigationMissionMode.ONCE
                else 1 + len(self._plan.targets) * self._plan.lap_count
            )
            self._pause_gate.set()
            self._status = NavigationMissionExecutionStatus(
                available=True,
                state=ActionState.RUNNING,
                mission_id=mission_id,
                mode=self._plan.mode,
                current_lap=(1 if self._plan.mode == NavigationMissionMode.ONCE else 0),
                total_laps=self._plan.lap_count,
                total_target_visits=total_visits,
                map_sequence=self._plan.map_sequence,
                reason="Preparing the first live route from fused localization",
            )
            self._task = asyncio.create_task(
                self._run(request), name=f"navigation-mission-{mission_id}"
            )
            return self._status

    async def pause(self) -> NavigationMissionExecutionStatus:
        if not self.running or self._status.state != ActionState.RUNNING:
            raise ActionConflictError("no running mission can be paused")
        self._pause_gate.clear()
        if self._execution is not None and self._execution.running:
            await self._execution.pause()
        self._status = self._status.model_copy(
            update={"state": ActionState.PAUSED, "reason": "Mission paused by operator"}
        )
        return self._status

    async def resume(self) -> NavigationMissionExecutionStatus:
        if not self.running or self._status.state != ActionState.PAUSED:
            raise ActionConflictError("no paused mission can be resumed")
        if not self._reviewed_map_is_current():
            await self._terminate(
                ActionState.BLOCKED, "occupancy map changed while paused"
            )
            return self._status
        if self._fresh_localization(self._plan.frame_id) is None:
            await self._terminate(ActionState.FAILED, "localization became stale")
            return self._status
        if (
            self._execution is not None
            and self._execution.running
            and self._execution.status.state == ActionState.PAUSED
        ):
            await self._execution.resume()
        self._status = self._status.model_copy(
            update={"state": ActionState.RUNNING, "reason": "Mission resumed"}
        )
        self._pause_gate.set()
        return self._status

    async def cancel(
        self, reason: str = "operator canceled"
    ) -> NavigationMissionExecutionStatus:
        if not self.running:
            return self._status
        await self._terminate(ActionState.CANCELED, reason)
        return self._status

    async def stop(self) -> None:
        if self.running:
            await self.cancel("service shutdown")

    async def _run(self, request: NavigationMissionExecutionRequest) -> None:
        try:
            targets = self._plan.targets
            if self._plan.mode == NavigationMissionMode.ONCE:
                visits = tuple((1, index) for index in range(len(targets)))
            else:
                visits = ((0, 0),) + tuple(
                    (lap, index)
                    for lap in range(1, self._plan.lap_count + 1)
                    for index in (*range(1, len(targets)), 0)
                )
            for lap, target_index in visits:
                await self._pause_gate.wait()
                if not self._reviewed_map_is_current():
                    await self._finish(ActionState.BLOCKED, "occupancy map changed")
                    return
                target = targets[target_index]
                pose = self._fresh_localization(self._plan.frame_id)
                if pose is None:
                    await self._finish(ActionState.FAILED, "localization became stale")
                    return
                self._status = self._status.model_copy(
                    update={
                        "current_lap": lap,
                        "active_target_index": target_index,
                        "reason": (
                            f"Planning target {target_index + 1} from the latest fused pose"
                        ),
                    }
                )
                if (
                    math.hypot(target.x_m - pose.x_m, target.y_m - pose.y_m)
                    > request.goal_tolerance_m
                ):
                    plan = await self._planning.plan(
                        self._goal_request_from_plan(target)
                    )
                    if (
                        plan.state != NavigationPlanState.READY
                        or not plan.geometry_validated
                        or plan.pose_source != "localization"
                    ):
                        await self._finish(
                            ActionState.BLOCKED,
                            f"live route to target {target_index + 1} was rejected: "
                            f"{plan.reason or plan.state.value}",
                        )
                        return
                    if plan.map_sequence != self._plan.map_sequence:
                        await self._finish(
                            ActionState.BLOCKED,
                            "live route used a different occupancy-map snapshot",
                        )
                        return
                    await self._pause_gate.wait()
                    if not self._reviewed_map_is_current():
                        await self._finish(
                            ActionState.BLOCKED,
                            "occupancy map changed before the live leg started",
                        )
                        return
                    self._status = self._status.model_copy(
                        update={
                            "current_leg_path_length_m": plan.path_length_m,
                            "reason": f"Following live route to target {target_index + 1}",
                        }
                    )
                    assert self._execution is not None
                    await self._execution.start(
                        NavigationExecutionRequest(
                            max_speed_mps=request.max_speed_mps,
                            lookahead_m=request.lookahead_m,
                            goal_tolerance_m=request.goal_tolerance_m,
                            timeout_seconds=request.leg_timeout_seconds,
                        )
                    )
                    while self._execution.running:
                        await asyncio.sleep(self._update_period_seconds)
                    result = self._execution.status
                    if result.state != ActionState.SUCCEEDED:
                        await self._finish(
                            result.state,
                            f"target {target_index + 1}: {result.reason or result.state.value}",
                        )
                        return
                    completed_distance = (
                        self._status.completed_distance_m + result.path_length_m
                    )
                else:
                    completed_distance = self._status.completed_distance_m
                self._status = self._status.model_copy(
                    update={
                        "completed_target_visits": (
                            self._status.completed_target_visits + 1
                        ),
                        "completed_distance_m": completed_distance,
                        "current_leg_path_length_m": 0.0,
                        "reason": f"Target {target_index + 1} reached",
                    }
                )
                if target.dwell_seconds > 0:
                    await self._dwell(target.dwell_seconds, target_index)
            await self._finish(ActionState.SUCCEEDED, "mission completed")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._finish(ActionState.FAILED, str(error))

    async def _dwell(self, seconds: float, target_index: int) -> None:
        remaining = seconds
        while remaining > 0:
            await self._pause_gate.wait()
            started = time.monotonic()
            self._status = self._status.model_copy(
                update={
                    "reason": (
                        f"Dwelling at target {target_index + 1} for "
                        f"{max(0.0, remaining):.1f} s"
                    )
                }
            )
            await asyncio.sleep(min(self._update_period_seconds, max(0.0, remaining)))
            if self._pause_gate.is_set():
                remaining -= max(0.0, time.monotonic() - started)

    async def _terminate(self, state: ActionState, reason: str) -> None:
        task = self._task
        self._task = None
        self._pause_gate.set()
        if self._execution is not None and self._execution.running:
            await self._execution.cancel(reason)
        if task is not None and not task.done() and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._finish(state, reason)

    async def _finish(self, state: ActionState, reason: str) -> None:
        self._task = None
        self._pause_gate.set()
        await self._planning.clear()
        self._status = self._status.model_copy(
            update={"state": state, "active_target_index": None, "reason": reason}
        )

    def _fresh_localization(self, frame_id: str) -> Optional[LocalizationPose2D]:
        pose = self._bus.latest(LOCALIZATION_POSE)
        if pose is None or pose.header.frame_id != frame_id:
            return None
        age = time.monotonic_ns() - pose.header.timestamp_monotonic_ns
        return pose if 0 <= age <= self._localization_timeout_ns else None

    def _reset_execution_status(self) -> None:
        self._status = (
            NavigationMissionExecutionStatus.idle()
            if self._execution is not None
            else NavigationMissionExecutionStatus.unavailable()
        )

    def _reviewed_map_is_current(self) -> bool:
        grid = self._bus.latest(LOCAL_MAP)
        return bool(
            grid is not None
            and self._plan.map_sequence is not None
            and self._same_map_sequence(grid, self._plan.map_sequence)
        )

    def _same_map_sequence(self, grid: OccupancyGrid, sequence: int) -> bool:
        return (
            grid.header.frame_id == self._plan.frame_id
            and grid.header.sequence == sequence
        )

    @staticmethod
    def _same_map(current: Optional[OccupancyGrid], reviewed: OccupancyGrid) -> bool:
        return bool(
            current is not None
            and current.header.frame_id == reviewed.header.frame_id
            and current.header.sequence == reviewed.header.sequence
        )

    @staticmethod
    def _goal_request(
        request: NavigationMissionReviewRequest, target: NavigationMissionTarget
    ) -> NavigationGoalRequest:
        return NavigationGoalRequest(
            x_m=target.x_m,
            y_m=target.y_m,
            clearance_m=request.clearance_m,
            allow_unknown=request.allow_unknown,
        )

    def _goal_request_from_plan(
        self, target: NavigationMissionTarget
    ) -> NavigationGoalRequest:
        return NavigationGoalRequest(
            x_m=target.x_m,
            y_m=target.y_m,
            clearance_m=(
                self._plan.legs[0].plan.clearance_m if self._plan.legs else 0.2
            ),
            allow_unknown=(
                self._plan.legs[0].plan.allow_unknown if self._plan.legs else False
            ),
        )

    @staticmethod
    def _terminal_vehicle_yaw(plan: NavigationPlanStatus, *, fallback: float) -> float:
        for index in range(len(plan.path) - 1, 0, -1):
            start = plan.path[index - 1]
            end = plan.path[index]
            delta_x = end.x_m - start.x_m
            delta_y = end.y_m - start.y_m
            if math.hypot(delta_x, delta_y) <= 1e-9:
                continue
            travel_yaw = math.atan2(delta_y, delta_x)
            direction = plan.path_directions[index - 1]
            return (
                travel_yaw
                if direction == NavigationDirection.FORWARD
                else NavigationMissionService._normalize_angle(travel_yaw + math.pi)
            )
        return fallback

    def _reject_review(
        self,
        request: NavigationMissionReviewRequest,
        reason: str,
        *,
        grid: Optional[OccupancyGrid] = None,
    ) -> NavigationMissionPlanStatus:
        self._plan = NavigationMissionPlanStatus(
            available=grid is not None,
            state=NavigationPlanState.REJECTED,
            frame_id=grid.header.frame_id if grid is not None else "odom",
            mode=request.mode,
            lap_count=request.lap_count,
            targets=request.targets,
            map_sequence=grid.header.sequence if grid is not None else None,
            reason=reason,
        )
        return self._plan

    def _fail_review(
        self,
        request: NavigationMissionReviewRequest,
        reason: str,
        grid: OccupancyGrid,
    ) -> NavigationMissionPlanStatus:
        self._plan = NavigationMissionPlanStatus(
            available=True,
            state=NavigationPlanState.FAILED,
            frame_id=grid.header.frame_id,
            mode=request.mode,
            lap_count=request.lap_count,
            targets=request.targets,
            map_sequence=grid.header.sequence,
            reason=reason,
        )
        return self._plan

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi


__all__ = ["NavigationMissionService"]
