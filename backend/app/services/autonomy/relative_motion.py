"""Cancelable odometry-bounded relative motion through the central arbiter."""

import asyncio
import math
import time
import uuid
from typing import Optional

from app.schemas.autonomy import (
    ActionState,
    Odometry2D,
    RelativeActionType,
    RelativeArcRequest,
    RelativeDistanceRequest,
    RelativeMotionStatus,
)
from app.services.autonomy.messages import MotionIntent, MotionSource, RobotMode
from app.services.autonomy.motion_control_service import MotionControlService
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import ODOMETRY


class ActionConflictError(RuntimeError):
    pass


class RelativeMotionService:
    """Execute one bounded straight-distance or fixed steering-arc action."""

    def __init__(
        self,
        bus: TopicBus,
        motion: MotionControlService,
        *,
        update_period_seconds: float = 0.05,
        odometry_timeout_seconds: float = 0.5,
        intent_timeout_seconds: float = 0.25,
        completion_tolerance_m: float = 0.01,
        wheelbase_m: Optional[float] = None,
        max_abs_steering_angle_rad: Optional[float] = None,
        yaw_tolerance_rad: float = math.radians(5),
    ) -> None:
        self._bus = bus
        self._motion = motion
        self._update_period_seconds = update_period_seconds
        self._odometry_timeout_ns = int(odometry_timeout_seconds * 1e9)
        self._intent_timeout_ns = int(intent_timeout_seconds * 1e9)
        self._completion_tolerance_m = completion_tolerance_m
        self._wheelbase_m = wheelbase_m
        self._max_abs_steering_angle_rad = max_abs_steering_angle_rad
        self._yaw_tolerance_rad = yaw_tolerance_rad
        self._task: Optional[asyncio.Task[None]] = None
        self._status = RelativeMotionStatus(
            available=True,
            max_abs_steering_angle_deg=(
                math.degrees(max_abs_steering_angle_rad)
                if max_abs_steering_angle_rad is not None
                else None
            ),
        )
        self._sequence = 0

    @property
    def status(self) -> RelativeMotionStatus:
        return self._status

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start_distance(
        self, request: RelativeDistanceRequest
    ) -> RelativeMotionStatus:
        return await self._start(
            request,
            action_type=RelativeActionType.DISTANCE,
            steering_angle_rad=0.0,
            target_yaw_rad=None,
        )

    async def start_arc(self, request: RelativeArcRequest) -> RelativeMotionStatus:
        if self._wheelbase_m is None or self._max_abs_steering_angle_rad is None:
            raise ActionConflictError(
                "arc motion requires calibrated steering geometry"
            )
        steering_angle_rad = math.radians(request.steering_angle_deg)
        if abs(steering_angle_rad) > self._max_abs_steering_angle_rad:
            raise ActionConflictError("requested steering exceeds the configured limit")
        target_yaw_rad = (
            -request.distance_m / self._wheelbase_m * math.tan(steering_angle_rad)
        )
        if abs(target_yaw_rad) > math.pi:
            raise ActionConflictError("predicted arc yaw must not exceed 180 degrees")
        return await self._start(
            request,
            action_type=RelativeActionType.ARC,
            steering_angle_rad=steering_angle_rad,
            target_yaw_rad=target_yaw_rad,
        )

    async def _start(
        self,
        request: RelativeDistanceRequest,
        *,
        action_type: RelativeActionType,
        steering_angle_rad: float,
        target_yaw_rad: Optional[float],
    ) -> RelativeMotionStatus:
        if self.running:
            raise ActionConflictError("an autonomous action is already running")
        if self._motion.mode in {RobotMode.ESTOP, RobotMode.FAULT}:
            raise ActionConflictError(f"robot mode is {self._motion.mode.value}")
        odometry = self._fresh_odometry()
        if odometry is None:
            raise ActionConflictError("fresh odometry is required")
        action_id = uuid.uuid4().hex
        owner = f"relative-motion:{action_id}"
        if not self._motion.claim_autonomy(owner):
            raise ActionConflictError("another autonomous action is already running")
        try:
            await self._motion.set_mode(RobotMode.AUTONOMOUS)
        except Exception:
            self._motion.release_autonomy(owner)
            raise
        timeout = request.timeout_seconds or max(
            2.0, abs(request.distance_m) / request.speed_mps * 2.0 + 1.0
        )
        self._status = RelativeMotionStatus(
            available=True,
            state=ActionState.RUNNING,
            action_id=action_id,
            action_type=action_type,
            distance_m=request.distance_m,
            requested_speed_mps=request.speed_mps,
            progress_m=0.0,
            remaining_m=abs(request.distance_m),
            steering_angle_deg=math.degrees(steering_angle_rad),
            max_abs_steering_angle_deg=(
                math.degrees(self._max_abs_steering_angle_rad)
                if self._max_abs_steering_angle_rad is not None
                else None
            ),
            target_yaw_rad=target_yaw_rad,
            yaw_progress_rad=0.0 if target_yaw_rad is not None else None,
        )
        self._task = asyncio.create_task(
            self._run(
                request,
                odometry,
                timeout,
                action_type=action_type,
                steering_angle_rad=steering_angle_rad,
                target_yaw_rad=target_yaw_rad,
            ),
            name=f"relative-{action_type.value}-{action_id}",
        )
        return self._status

    async def cancel(self, reason: str = "operator canceled") -> RelativeMotionStatus:
        if not self.running:
            return self._status
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._finish(ActionState.CANCELED, reason)
        return self._status

    async def stop(self) -> None:
        if self.running:
            await self.cancel("service shutdown")

    def _fresh_odometry(self) -> Optional[Odometry2D]:
        odometry = self._bus.latest(ODOMETRY)
        if odometry is None:
            return None
        age = time.monotonic_ns() - odometry.header.timestamp_monotonic_ns
        return odometry if 0 <= age <= self._odometry_timeout_ns else None

    async def _run(
        self,
        request: RelativeDistanceRequest,
        start: Odometry2D,
        timeout_seconds: float,
        *,
        action_type: RelativeActionType,
        steering_angle_rad: float,
        target_yaw_rad: Optional[float],
    ) -> None:
        started_ns = time.monotonic_ns()
        direction = 1.0 if request.distance_m > 0 else -1.0
        target = abs(request.distance_m)
        previous_odometry = start
        path_progress = 0.0
        try:
            while True:
                if self._motion.mode != RobotMode.AUTONOMOUS:
                    await self._finish(
                        ActionState.CANCELED,
                        f"robot mode changed to {self._motion.mode.value}",
                        change_mode=False,
                    )
                    return
                now = time.monotonic_ns()
                if now - started_ns > int(timeout_seconds * 1e9):
                    await self._finish(ActionState.FAILED, "action timed out")
                    return
                odometry = self._fresh_odometry()
                if odometry is None:
                    await self._finish(ActionState.FAILED, "odometry became stale")
                    return
                dx = odometry.x_m - start.x_m
                dy = odometry.y_m - start.y_m
                if action_type == RelativeActionType.ARC:
                    if odometry.header.sequence != previous_odometry.header.sequence:
                        path_progress += math.hypot(
                            odometry.x_m - previous_odometry.x_m,
                            odometry.y_m - previous_odometry.y_m,
                        )
                        previous_odometry = odometry
                    progress = path_progress
                else:
                    progress = max(
                        0.0,
                        direction
                        * (dx * math.cos(start.yaw_rad) + dy * math.sin(start.yaw_rad)),
                    )
                remaining = max(0.0, target - progress)
                yaw_progress = (
                    self._normalize_angle(odometry.yaw_rad - start.yaw_rad)
                    if target_yaw_rad is not None
                    else None
                )
                self._status = self._status.model_copy(
                    update={
                        "progress_m": progress,
                        "remaining_m": remaining,
                        "yaw_progress_rad": yaw_progress,
                    }
                )
                if remaining <= self._completion_tolerance_m:
                    if (
                        target_yaw_rad is not None
                        and yaw_progress is not None
                        and abs(self._normalize_angle(target_yaw_rad - yaw_progress))
                        > self._yaw_tolerance_rad
                    ):
                        await self._finish(
                            ActionState.FAILED,
                            "measured yaw did not match predicted arc curvature",
                        )
                        return
                    await self._finish(
                        ActionState.SUCCEEDED,
                        (
                            "target arc reached"
                            if action_type == RelativeActionType.ARC
                            else "target distance reached"
                        ),
                    )
                    return
                result = self._motion.last_result
                if (
                    result is not None
                    and result.selected_intent is not None
                    and result.selected_intent.source == MotionSource.AUTONOMY
                    and result.command.is_stop
                    and result.command.reason
                ):
                    await self._finish(ActionState.BLOCKED, result.command.reason)
                    return
                speed = min(request.speed_mps, max(0.04, remaining * 1.5))
                self._sequence += 1
                intent = MotionIntent(
                    command_id=self._status.action_id or "relative-distance",
                    source=MotionSource.AUTONOMY,
                    sequence=self._sequence,
                    mode_generation=self._motion.mode_generation,
                    linear_speed_mps=direction * speed,
                    steering_angle_rad=steering_angle_rad,
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
                await asyncio.sleep(self._update_period_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._finish(ActionState.FAILED, str(error))

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi

    async def _finish(
        self,
        state: ActionState,
        reason: str,
        *,
        change_mode: bool = True,
    ) -> None:
        self._motion.revoke(MotionSource.AUTONOMY)
        if change_mode and self._motion.mode == RobotMode.AUTONOMOUS:
            await self._motion.set_mode(RobotMode.DISARMED)
        if self._status.action_id is not None:
            self._motion.release_autonomy(f"relative-motion:{self._status.action_id}")
        self._status = self._status.model_copy(
            update={
                "state": state,
                "reason": reason,
                "remaining_m": (
                    0.0 if state == ActionState.SUCCEEDED else self._status.remaining_m
                ),
            }
        )


__all__ = ["ActionConflictError", "RelativeMotionService"]
