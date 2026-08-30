"""Cancelable odometry-bounded relative motion through the central arbiter."""

import asyncio
import math
import time
import uuid
from typing import Optional

from app.schemas.autonomy import (
    ActionState,
    Odometry2D,
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
    """Execute one straight relative-distance action at a time."""

    def __init__(
        self,
        bus: TopicBus,
        motion: MotionControlService,
        *,
        update_period_seconds: float = 0.05,
        odometry_timeout_seconds: float = 0.5,
        intent_timeout_seconds: float = 0.25,
        completion_tolerance_m: float = 0.01,
    ) -> None:
        self._bus = bus
        self._motion = motion
        self._update_period_seconds = update_period_seconds
        self._odometry_timeout_ns = int(odometry_timeout_seconds * 1e9)
        self._intent_timeout_ns = int(intent_timeout_seconds * 1e9)
        self._completion_tolerance_m = completion_tolerance_m
        self._task: Optional[asyncio.Task[None]] = None
        self._status = RelativeMotionStatus(available=True)
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
        if self.running:
            raise ActionConflictError("an autonomous action is already running")
        if self._motion.mode in {RobotMode.ESTOP, RobotMode.FAULT}:
            raise ActionConflictError(f"robot mode is {self._motion.mode.value}")
        odometry = self._fresh_odometry()
        if odometry is None:
            raise ActionConflictError("fresh odometry is required")
        await self._motion.set_mode(RobotMode.AUTONOMOUS)
        action_id = uuid.uuid4().hex
        timeout = request.timeout_seconds or max(
            2.0, abs(request.distance_m) / request.speed_mps * 2.0 + 1.0
        )
        self._status = RelativeMotionStatus(
            available=True,
            state=ActionState.RUNNING,
            action_id=action_id,
            distance_m=request.distance_m,
            requested_speed_mps=request.speed_mps,
            progress_m=0.0,
            remaining_m=abs(request.distance_m),
        )
        self._task = asyncio.create_task(
            self._run(request, odometry, timeout),
            name=f"relative-distance-{action_id}",
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
    ) -> None:
        started_ns = time.monotonic_ns()
        direction = 1.0 if request.distance_m > 0 else -1.0
        target = abs(request.distance_m)
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
                progress = max(
                    0.0,
                    direction
                    * (dx * math.cos(start.yaw_rad) + dy * math.sin(start.yaw_rad)),
                )
                remaining = max(0.0, target - progress)
                self._status = self._status.model_copy(
                    update={"progress_m": progress, "remaining_m": remaining}
                )
                if remaining <= self._completion_tolerance_m:
                    await self._finish(ActionState.SUCCEEDED, "target distance reached")
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
                    steering_angle_rad=0.0,
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
