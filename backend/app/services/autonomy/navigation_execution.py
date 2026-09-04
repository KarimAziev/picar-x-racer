"""Cancelable pure-pursuit execution of one reviewed navigation route."""

import asyncio
import math
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from app.schemas.autonomy import (
    ActionState,
    LocalizationPose2D,
    NavigationExecutionRequest,
    NavigationExecutionStatus,
    NavigationPlanState,
    NavigationPoint,
)
from app.services.autonomy.messages import MotionIntent, MotionSource, RobotMode
from app.services.autonomy.motion_control_service import MotionControlService
from app.services.autonomy.navigation_planning import NavigationPlanningService
from app.services.autonomy.relative_motion import ActionConflictError
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP


@dataclass(frozen=True)
class TrackingSolution:
    progress_m: float
    remaining_m: float
    cross_track_error_m: float
    target: NavigationPoint
    target_waypoint_index: int
    steering_angle_rad: float


class PurePursuitTracker:
    """Project a pose onto a polyline and select a forward lookahead target."""

    def __init__(
        self,
        path: Sequence[NavigationPoint],
        *,
        wheelbase_m: float,
        max_abs_steering_angle_rad: float,
        lookahead_m: float,
    ) -> None:
        if len(path) < 2:
            raise ValueError("navigation path must contain at least two points")
        if wheelbase_m <= 0 or max_abs_steering_angle_rad <= 0 or lookahead_m <= 0:
            raise ValueError("tracking geometry must be positive")
        self.path = tuple(path)
        self.wheelbase_m = wheelbase_m
        self.max_abs_steering_angle_rad = max_abs_steering_angle_rad
        self.lookahead_m = lookahead_m
        cumulative = [0.0]
        for start, end in zip(self.path, self.path[1:]):
            length = math.hypot(end.x_m - start.x_m, end.y_m - start.y_m)
            if length <= 1e-9:
                raise ValueError("navigation path contains a zero-length segment")
            cumulative.append(cumulative[-1] + length)
        self.cumulative_lengths = tuple(cumulative)
        self.total_length_m = cumulative[-1]
        self._progress_m = 0.0

    def update(self, pose: LocalizationPose2D) -> TrackingSolution:
        projected_progress, cross_track = self._project(pose.x_m, pose.y_m)
        self._progress_m = max(self._progress_m, projected_progress)
        remaining = max(0.0, self.total_length_m - self._progress_m)
        target, target_index = self._point_at(
            min(self.total_length_m, self._progress_m + self.lookahead_m)
        )
        delta_x = target.x_m - pose.x_m
        delta_y = target.y_m - pose.y_m
        target_distance = max(1e-6, math.hypot(delta_x, delta_y))
        heading_error = self._normalize_angle(
            math.atan2(delta_y, delta_x) - pose.yaw_rad
        )
        # This project defines negative steering as left. The leading minus
        # converts conventional positive counter-clockwise heading error into
        # the actuator convention used by the Ackermann plant and hardware.
        steering = -math.atan2(
            2.0 * self.wheelbase_m * math.sin(heading_error),
            target_distance,
        )
        steering = max(
            -self.max_abs_steering_angle_rad,
            min(self.max_abs_steering_angle_rad, steering),
        )
        return TrackingSolution(
            progress_m=self._progress_m,
            remaining_m=remaining,
            cross_track_error_m=cross_track,
            target=target,
            target_waypoint_index=target_index,
            steering_angle_rad=steering,
        )

    def _project(self, x_m: float, y_m: float) -> Tuple[float, float]:
        best_distance = math.inf
        best_progress = self._progress_m
        for index, (start, end) in enumerate(zip(self.path, self.path[1:])):
            delta_x = end.x_m - start.x_m
            delta_y = end.y_m - start.y_m
            length_squared = delta_x * delta_x + delta_y * delta_y
            fraction = max(
                0.0,
                min(
                    1.0,
                    ((x_m - start.x_m) * delta_x + (y_m - start.y_m) * delta_y)
                    / length_squared,
                ),
            )
            projected_x = start.x_m + fraction * delta_x
            projected_y = start.y_m + fraction * delta_y
            distance = math.hypot(x_m - projected_x, y_m - projected_y)
            progress = self.cumulative_lengths[index] + fraction * math.sqrt(
                length_squared
            )
            if distance < best_distance or (
                math.isclose(distance, best_distance) and progress > best_progress
            ):
                best_distance = distance
                best_progress = progress
        return best_progress, best_distance

    def _point_at(self, distance_m: float) -> Tuple[NavigationPoint, int]:
        for index in range(1, len(self.path)):
            segment_end = self.cumulative_lengths[index]
            if distance_m > segment_end and index < len(self.path) - 1:
                continue
            segment_start = self.cumulative_lengths[index - 1]
            fraction = (distance_m - segment_start) / (segment_end - segment_start)
            start = self.path[index - 1]
            end = self.path[index]
            return (
                NavigationPoint(
                    x_m=start.x_m + fraction * (end.x_m - start.x_m),
                    y_m=start.y_m + fraction * (end.y_m - start.y_m),
                ),
                index,
            )
        return self.path[-1], len(self.path) - 1

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi


class NavigationExecutionService:
    """Follow the currently reviewed route through the central motion arbiter."""

    def __init__(
        self,
        bus: TopicBus,
        motion: MotionControlService,
        planning: NavigationPlanningService,
        *,
        wheelbase_m: float,
        max_abs_steering_angle_rad: float,
        update_period_seconds: float = 0.05,
        localization_timeout_seconds: float = 0.5,
        intent_timeout_seconds: float = 0.25,
        max_cross_track_error_m: float = 0.35,
        max_start_position_error_m: float = 0.15,
        max_start_heading_error_rad: float = math.radians(15.0),
    ) -> None:
        if max_start_position_error_m <= 0:
            raise ValueError("maximum start-position error must be positive")
        if not 0 < max_start_heading_error_rad < math.pi:
            raise ValueError("maximum start-heading error must be between zero and pi")
        self._bus = bus
        self._motion = motion
        self._planning = planning
        self._wheelbase_m = wheelbase_m
        self._max_abs_steering_angle_rad = max_abs_steering_angle_rad
        self._update_period_seconds = update_period_seconds
        self._localization_timeout_ns = int(localization_timeout_seconds * 1e9)
        self._intent_timeout_ns = int(intent_timeout_seconds * 1e9)
        self._max_cross_track_error_m = max_cross_track_error_m
        self._max_start_position_error_m = max_start_position_error_m
        self._max_start_heading_error_rad = max_start_heading_error_rad
        self._task: Optional[asyncio.Task[None]] = None
        self._status = NavigationExecutionStatus.idle()
        self._sequence = 0
        self._paused = False

    @property
    def status(self) -> NavigationExecutionStatus:
        return self._status

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(
        self, request: NavigationExecutionRequest
    ) -> NavigationExecutionStatus:
        if self.running:
            raise ActionConflictError("a navigation action is already running")
        if self._motion.mode in {RobotMode.ESTOP, RobotMode.FAULT}:
            raise ActionConflictError(f"robot mode is {self._motion.mode.value}")
        plan = self._planning.status
        if plan.state != NavigationPlanState.READY or plan.goal is None:
            raise ActionConflictError("a ready navigation route is required")
        if len(plan.path) < 2 or plan.map_sequence is None:
            raise ActionConflictError("the navigation route is incomplete")
        if not plan.geometry_validated:
            raise ActionConflictError(
                "the navigation route was not validated for Ackermann geometry"
            )
        if (
            plan.pose_source != "localization"
            or plan.start is None
            or plan.start_yaw_rad is None
        ):
            raise ActionConflictError(
                "review a new route after fresh fused localization is available"
            )
        grid = self._bus.latest(LOCAL_MAP)
        if grid is None or grid.header.sequence != plan.map_sequence:
            raise ActionConflictError("the occupancy map changed; review a new route")
        pose = self._fresh_localization(plan.frame_id)
        if pose is None:
            raise ActionConflictError("fresh fused localization is required")
        start_position_error_m = math.hypot(
            pose.x_m - plan.start.x_m,
            pose.y_m - plan.start.y_m,
        )
        if start_position_error_m > self._max_start_position_error_m:
            raise ActionConflictError(
                "the vehicle moved "
                f"{start_position_error_m:.2f} m since route review; review a new route"
            )
        start_heading_error_rad = abs(
            self._normalize_angle(pose.yaw_rad - plan.start_yaw_rad)
        )
        if start_heading_error_rad > self._max_start_heading_error_rad:
            raise ActionConflictError(
                "the vehicle heading changed "
                f"{math.degrees(start_heading_error_rad):.1f} degrees since route review; "
                "review a new route"
            )

        tracker = PurePursuitTracker(
            plan.path,
            wheelbase_m=self._wheelbase_m,
            max_abs_steering_angle_rad=self._max_abs_steering_angle_rad,
            lookahead_m=request.lookahead_m,
        )
        action_id = uuid.uuid4().hex
        owner = f"navigation:{action_id}"
        if not self._motion.claim_autonomy(owner):
            raise ActionConflictError("another autonomous action is already running")
        try:
            await self._motion.set_mode(RobotMode.AUTONOMOUS)
        except Exception:
            self._motion.release_autonomy(owner)
            raise

        timeout_seconds = request.timeout_seconds or min(
            300.0,
            max(10.0, plan.path_length_m / request.max_speed_mps * 4.0 + 5.0),
        )
        self._paused = False
        self._status = NavigationExecutionStatus(
            available=True,
            state=ActionState.RUNNING,
            action_id=action_id,
            goal=plan.goal,
            current_pose=NavigationPoint(x_m=pose.x_m, y_m=pose.y_m),
            map_sequence=plan.map_sequence,
            path_length_m=plan.path_length_m,
            remaining_m=plan.path_length_m,
            max_speed_mps=request.max_speed_mps,
            reason="Following the reviewed route",
        )
        self._task = asyncio.create_task(
            self._run(request, tracker, timeout_seconds, plan.frame_id),
            name=f"navigation-{action_id}",
        )
        return self._status

    async def pause(self) -> NavigationExecutionStatus:
        if not self.running or self._status.state != ActionState.RUNNING:
            raise ActionConflictError("no running navigation action can be paused")
        self._paused = True
        self._motion.revoke(MotionSource.AUTONOMY)
        if self._motion.mode == RobotMode.AUTONOMOUS:
            await self._motion.set_mode(RobotMode.DISARMED)
        self._status = self._status.model_copy(
            update={
                "state": ActionState.PAUSED,
                "commanded_speed_mps": 0.0,
                "steering_angle_deg": 0.0,
                "reason": "Navigation paused by operator",
            }
        )
        return self._status

    async def resume(self) -> NavigationExecutionStatus:
        if not self.running or self._status.state != ActionState.PAUSED:
            raise ActionConflictError("no paused navigation action can be resumed")
        plan = self._planning.status
        grid = self._bus.latest(LOCAL_MAP)
        if (
            plan.state != NavigationPlanState.READY
            or plan.map_sequence != self._status.map_sequence
            or grid is None
            or grid.header.sequence != self._status.map_sequence
        ):
            await self._terminate(
                ActionState.BLOCKED, "route or map changed while paused"
            )
            return self._status
        if self._fresh_localization(plan.frame_id) is None:
            await self._terminate(ActionState.FAILED, "localization became stale")
            return self._status
        await self._motion.set_mode(RobotMode.AUTONOMOUS)
        self._paused = False
        self._status = self._status.model_copy(
            update={"state": ActionState.RUNNING, "reason": "Navigation resumed"}
        )
        return self._status

    async def cancel(
        self, reason: str = "operator canceled"
    ) -> NavigationExecutionStatus:
        if not self.running:
            return self._status
        await self._terminate(ActionState.CANCELED, reason)
        return self._status

    async def _terminate(self, state: ActionState, reason: str) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._finish(state, reason)

    async def stop(self) -> None:
        if self.running:
            await self.cancel("service shutdown")

    async def _run(
        self,
        request: NavigationExecutionRequest,
        tracker: PurePursuitTracker,
        timeout_seconds: float,
        frame_id: str,
    ) -> None:
        active_elapsed_ns = 0
        previous_loop_ns = time.monotonic_ns()
        try:
            while True:
                now = time.monotonic_ns()
                elapsed = max(0, now - previous_loop_ns)
                previous_loop_ns = now
                if not self._route_snapshot_is_current(frame_id):
                    await self._finish(
                        ActionState.BLOCKED,
                        "route or occupancy map changed; review a new route",
                    )
                    return
                if self._paused:
                    if self._motion.mode not in {
                        RobotMode.DISARMED,
                        RobotMode.AUTONOMOUS,
                    }:
                        await self._finish(
                            ActionState.CANCELED,
                            f"robot mode changed to {self._motion.mode.value}",
                            change_mode=False,
                        )
                        return
                    await asyncio.sleep(self._update_period_seconds)
                    continue
                active_elapsed_ns += elapsed
                if self._motion.mode != RobotMode.AUTONOMOUS:
                    await self._finish(
                        ActionState.CANCELED,
                        f"robot mode changed to {self._motion.mode.value}",
                        change_mode=False,
                    )
                    return
                if active_elapsed_ns > int(timeout_seconds * 1e9):
                    await self._finish(ActionState.FAILED, "navigation timed out")
                    return
                pose = self._fresh_localization(frame_id)
                if pose is None:
                    await self._finish(ActionState.FAILED, "localization became stale")
                    return
                solution = tracker.update(pose)
                goal = self._status.goal
                if goal is None:
                    await self._finish(
                        ActionState.FAILED, "navigation goal disappeared"
                    )
                    return
                distance_to_goal = math.hypot(goal.x_m - pose.x_m, goal.y_m - pose.y_m)
                self._status = self._status.model_copy(
                    update={
                        "current_pose": NavigationPoint(x_m=pose.x_m, y_m=pose.y_m),
                        "progress_m": solution.progress_m,
                        "remaining_m": solution.remaining_m,
                        "target_waypoint_index": solution.target_waypoint_index,
                        "cross_track_error_m": solution.cross_track_error_m,
                    }
                )
                if distance_to_goal <= request.goal_tolerance_m:
                    await self._finish(ActionState.SUCCEEDED, "navigation goal reached")
                    return
                if solution.cross_track_error_m > self._max_cross_track_error_m:
                    await self._finish(
                        ActionState.FAILED,
                        "vehicle departed too far from the reviewed route",
                    )
                    return
                result = self._motion.last_result
                if (
                    result is not None
                    and result.selected_intent is not None
                    and result.selected_intent.command_id == self._status.action_id
                    and result.command.is_stop
                    and result.command.reason
                ):
                    await self._finish(ActionState.BLOCKED, result.command.reason)
                    return
                speed = self._commanded_speed(request, solution)
                self._sequence += 1
                intent = MotionIntent(
                    command_id=self._status.action_id or "navigation",
                    source=MotionSource.AUTONOMY,
                    sequence=self._sequence,
                    mode_generation=self._motion.mode_generation,
                    linear_speed_mps=speed,
                    steering_angle_rad=solution.steering_angle_rad,
                    created_monotonic_ns=now,
                    expires_monotonic_ns=now + self._intent_timeout_ns,
                )
                submission = self._motion.submit(intent)
                if not submission.accepted:
                    await self._finish(
                        ActionState.FAILED,
                        f"motion intent rejected: {submission.rejection_reason}",
                    )
                    return
                self._status = self._status.model_copy(
                    update={
                        "commanded_speed_mps": speed,
                        "steering_angle_deg": math.degrees(solution.steering_angle_rad),
                        "reason": "Following the reviewed route",
                    }
                )
                await asyncio.sleep(self._update_period_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._finish(ActionState.FAILED, str(error))

    def _route_snapshot_is_current(self, frame_id: str) -> bool:
        plan = self._planning.status
        grid = self._bus.latest(LOCAL_MAP)
        return bool(
            plan.state == NavigationPlanState.READY
            and plan.frame_id == frame_id
            and plan.map_sequence == self._status.map_sequence
            and plan.goal == self._status.goal
            and grid is not None
            and grid.header.frame_id == frame_id
            and grid.header.sequence == self._status.map_sequence
        )

    def _fresh_localization(self, frame_id: str) -> Optional[LocalizationPose2D]:
        pose = self._bus.latest(LOCALIZATION_POSE)
        if pose is None or pose.header.frame_id != frame_id:
            return None
        age = time.monotonic_ns() - pose.header.timestamp_monotonic_ns
        return pose if 0 <= age <= self._localization_timeout_ns else None

    def _commanded_speed(
        self,
        request: NavigationExecutionRequest,
        solution: TrackingSolution,
    ) -> float:
        stopping_speed = max(0.04, min(request.max_speed_mps, solution.remaining_m))
        steering_fraction = min(
            1.0,
            abs(solution.steering_angle_rad) / self._max_abs_steering_angle_rad,
        )
        curvature_scale = max(0.35, 1.0 - 0.65 * steering_fraction)
        return min(request.max_speed_mps, stopping_speed * curvature_scale)

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi

    async def _finish(
        self,
        state: ActionState,
        reason: str,
        *,
        change_mode: bool = True,
    ) -> None:
        self._paused = False
        self._motion.revoke(MotionSource.AUTONOMY)
        if change_mode and self._motion.mode == RobotMode.AUTONOMOUS:
            await self._motion.set_mode(RobotMode.DISARMED)
        if self._status.action_id is not None:
            self._motion.release_autonomy(f"navigation:{self._status.action_id}")
        self._status = self._status.model_copy(
            update={
                "state": state,
                "progress_m": (
                    self._status.path_length_m
                    if state == ActionState.SUCCEEDED
                    else self._status.progress_m
                ),
                "remaining_m": (
                    0.0 if state == ActionState.SUCCEEDED else self._status.remaining_m
                ),
                "commanded_speed_mps": 0.0,
                "steering_angle_deg": 0.0,
                "reason": reason,
            }
        )


__all__ = [
    "NavigationExecutionService",
    "PurePursuitTracker",
    "TrackingSolution",
]
