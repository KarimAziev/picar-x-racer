"""Watchdog-driven execution of resolved motion commands."""

import asyncio
from typing import Dict, Optional

from app.services.autonomy.actuation import HardwareController
from app.services.autonomy.messages import (
    ArbitrationResult,
    IntentSubmissionResult,
    MotionIntent,
    MotionSource,
    RobotMode,
    SafetyConstraint,
)
from app.services.autonomy.motion_arbiter import MotionArbiter


class ModeTransitionError(RuntimeError):
    """Raised when attempting to bypass a latched safety mode."""


class MotionControlService:
    """Own robot mode, run arbitration periodically, and feed one hardware writer."""

    def __init__(
        self,
        arbiter: MotionArbiter,
        hardware_controller: HardwareController,
        *,
        control_period_seconds: float = 0.05,
    ) -> None:
        if control_period_seconds <= 0:
            raise ValueError("control_period_seconds must be greater than zero")
        self._arbiter = arbiter
        self._hardware_controller = hardware_controller
        self._control_period_seconds = control_period_seconds
        self._mode = RobotMode.DISARMED
        self._mode_generation = 0
        self._constraints: Dict[str, SafetyConstraint] = {}
        self._task: Optional[asyncio.Task[None]] = None
        self._apply_lock = asyncio.Lock()
        self._last_result: Optional[ArbitrationResult] = None
        self._last_error: Optional[Exception] = None
        self._estop_reason: Optional[str] = None

    @property
    def mode(self) -> RobotMode:
        return self._mode

    @property
    def mode_generation(self) -> int:
        return self._mode_generation

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def last_result(self) -> Optional[ArbitrationResult]:
        return self._last_result

    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error

    @property
    def control_period_seconds(self) -> float:
        return self._control_period_seconds

    @property
    def estop_reason(self) -> Optional[str]:
        return self._estop_reason

    def submit(self, intent: MotionIntent) -> IntentSubmissionResult:
        """Submit against the current mode and its anti-replay generation."""

        return self._arbiter.submit(
            intent,
            mode=self._mode,
            mode_generation=self._mode_generation,
        )

    def revoke(self, source: MotionSource) -> None:
        self._arbiter.revoke(source)

    def put_constraint(self, constraint: SafetyConstraint) -> None:
        self._constraints[constraint.constraint_id] = constraint

    def remove_constraint(self, constraint_id: str) -> None:
        self._constraints.pop(constraint_id, None)

    async def set_mode(self, mode: RobotMode) -> ArbitrationResult:
        """Invalidate old intents and apply the new mode's safe output immediately."""

        if self._mode == RobotMode.ESTOP and mode != RobotMode.ESTOP:
            raise ModeTransitionError(
                "emergency stop is latched; clear it before changing mode"
            )
        if self._mode == RobotMode.FAULT and mode != RobotMode.FAULT:
            raise ModeTransitionError("fault is latched; clear it before changing mode")
        if mode == RobotMode.ESTOP:
            return await self.emergency_stop("emergency stop requested")
        return await self._set_mode_unchecked(mode)

    async def emergency_stop(self, reason: str) -> ArbitrationResult:
        """Latch emergency stop and synchronously apply a safe output."""

        if not reason.strip():
            raise ValueError("emergency stop reason must not be empty")
        self._estop_reason = reason
        if self._mode == RobotMode.FAULT:
            return await self.step()
        return await self._set_mode_unchecked(RobotMode.ESTOP)

    async def clear_emergency_stop(self) -> ArbitrationResult:
        """Clear an ESTOP into DISARMED; re-arming requires another transition."""

        if self._mode != RobotMode.ESTOP:
            raise ModeTransitionError("robot is not in emergency stop mode")
        self._estop_reason = None
        return await self._set_mode_unchecked(RobotMode.DISARMED)

    async def clear_fault(self) -> ArbitrationResult:
        """Attempt to clear a fault into DISARMED and re-assert hardware stop."""

        if self._mode != RobotMode.FAULT:
            raise ModeTransitionError("robot is not in fault mode")
        self._last_error = None
        return await self._set_mode_unchecked(RobotMode.DISARMED)

    async def _set_mode_unchecked(self, mode: RobotMode) -> ArbitrationResult:
        if mode != self._mode:
            self._mode = mode
            self._mode_generation += 1
            self._arbiter.clear()
        return await self.step()

    async def step(self) -> ArbitrationResult:
        """Resolve and apply exactly one watchdog cycle."""

        async with self._apply_lock:
            result = self._arbiter.resolve(
                mode=self._mode,
                mode_generation=self._mode_generation,
                constraints=self._constraints.values(),
            )
            try:
                await asyncio.to_thread(
                    self._hardware_controller.apply,
                    result.command,
                )
            except Exception as error:
                self._transition_to_fault(error)
                raise
            self._last_result = result
            return result

    def start(self) -> None:
        """Start periodic watchdog execution on the current event loop."""

        if self.running:
            return
        self._last_error = None
        self._task = asyncio.create_task(self._run(), name="motion-control-watchdog")

    async def stop(self) -> None:
        """Stop the loop and issue an unconditional hardware stop."""

        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as error:
                self._last_error = error
        async with self._apply_lock:
            await asyncio.to_thread(self._hardware_controller.force_stop)

    async def _run(self) -> None:
        try:
            while True:
                await self.step()
                await asyncio.sleep(self._control_period_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._transition_to_fault(error)

    def _transition_to_fault(self, error: Exception) -> None:
        self._last_error = error
        if self._mode != RobotMode.FAULT:
            self._mode = RobotMode.FAULT
            self._mode_generation += 1
            self._arbiter.clear()


__all__ = ["ModeTransitionError", "MotionControlService"]
