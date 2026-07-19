"""Mode-aware selection and safety limiting of expiring motion intents."""

from typing import Dict, Iterable, Optional, Set, Tuple

from app.services.autonomy.clock import Clock, SystemClock
from app.services.autonomy.messages import (
    ActuatorCommand,
    ArbitrationResult,
    IntentRejectionReason,
    IntentSubmissionResult,
    MotionIntent,
    MotionLimits,
    MotionSource,
    RobotMode,
    SafetyConstraint,
    SafetySeverity,
)


ELIGIBLE_SOURCES: Dict[RobotMode, Set[MotionSource]] = {
    RobotMode.DISARMED: set(),
    RobotMode.MANUAL: {MotionSource.MANUAL},
    RobotMode.AUTONOMOUS: {MotionSource.AUTONOMY},
    RobotMode.CALIBRATION: {MotionSource.CALIBRATION},
    RobotMode.ESTOP: set(),
    RobotMode.FAULT: set(),
}

COMMANDABLE_SOURCES = {
    MotionSource.MANUAL,
    MotionSource.AUTONOMY,
    MotionSource.CALIBRATION,
}


class MotionArbiter:
    """Retain current intents and resolve one safe actuator command."""

    def __init__(self, limits: MotionLimits, clock: Optional[Clock] = None) -> None:
        self.limits = limits
        self.clock = clock or SystemClock()
        self._latest_intents: Dict[MotionSource, MotionIntent] = {}
        self._last_sequences: Dict[MotionSource, Tuple[int, int]] = {}

    def submit(
        self,
        intent: MotionIntent,
        *,
        mode: RobotMode,
        mode_generation: int,
    ) -> IntentSubmissionResult:
        """Validate and retain an intent if it is current and eligible."""

        if intent.source not in COMMANDABLE_SOURCES:
            return self._reject(intent, IntentRejectionReason.SOURCE_NOT_COMMANDABLE)
        if intent.mode_generation != mode_generation:
            return self._reject(intent, IntentRejectionReason.WRONG_MODE_GENERATION)
        if intent.source not in ELIGIBLE_SOURCES[mode]:
            return self._reject(intent, IntentRejectionReason.WRONG_MODE)

        now = self.clock.monotonic_ns()
        if intent.created_monotonic_ns > now:
            return self._reject(intent, IntentRejectionReason.CREATED_IN_FUTURE)

        sequence_state = self._last_sequences.get(intent.source)
        if (
            sequence_state is not None
            and sequence_state[0] == mode_generation
            and intent.sequence <= sequence_state[1]
        ):
            return self._reject(intent, IntentRejectionReason.STALE_SEQUENCE)

        self._last_sequences[intent.source] = (mode_generation, intent.sequence)
        if intent.expires_monotonic_ns <= now:
            self._latest_intents.pop(intent.source, None)
            return self._reject(intent, IntentRejectionReason.EXPIRED)

        self._latest_intents[intent.source] = intent
        return IntentSubmissionResult(intent=intent, accepted=True)

    def revoke(self, source: MotionSource) -> None:
        """Remove the currently retained intent for a source."""

        self._latest_intents.pop(source, None)

    def clear(self) -> None:
        """Remove retained intents without resetting replay protection."""

        self._latest_intents.clear()

    def resolve(
        self,
        *,
        mode: RobotMode,
        mode_generation: int,
        constraints: Iterable[SafetyConstraint] = (),
    ) -> ArbitrationResult:
        """Select one valid intent and apply current limits and safety constraints."""

        now = self.clock.monotonic_ns()
        active_constraints = tuple(
            constraint
            for constraint in constraints
            if constraint.created_monotonic_ns <= now
            and (
                constraint.expires_monotonic_ns is None
                or constraint.expires_monotonic_ns > now
            )
        )

        selected = self._select_intent(mode, mode_generation, now)

        if mode in {RobotMode.ESTOP, RobotMode.FAULT}:
            return self._stop_result(
                now,
                selected,
                active_constraints,
                reason=f"robot mode is {mode.value}",
                source=MotionSource.SAFETY,
            )
        if mode == RobotMode.DISARMED:
            return self._stop_result(
                now,
                selected,
                active_constraints,
                reason="robot is disarmed",
            )

        emergency_constraints = tuple(
            constraint
            for constraint in active_constraints
            if constraint.severity == SafetySeverity.ESTOP
        )
        if emergency_constraints:
            return self._stop_result(
                now,
                selected,
                active_constraints,
                limiting_constraints=emergency_constraints,
                reason=self._constraint_reason(emergency_constraints),
                source=MotionSource.SAFETY,
            )

        stop_constraints = tuple(
            constraint
            for constraint in active_constraints
            if constraint.severity == SafetySeverity.STOP
        )
        if stop_constraints:
            return self._stop_result(
                now,
                selected,
                active_constraints,
                limiting_constraints=stop_constraints,
                reason=self._constraint_reason(stop_constraints),
                source=MotionSource.SAFETY,
            )

        if selected is None:
            return self._stop_result(
                now,
                None,
                active_constraints,
                reason="no valid motion intent",
            )

        speed = self._clamp_speed(selected.linear_speed_mps)
        steering = self._clamp(
            selected.steering_angle_rad,
            -self.limits.max_abs_steering_angle_rad,
            self.limits.max_abs_steering_angle_rad,
        )
        limiting_constraints = []
        for constraint in active_constraints:
            if constraint.severity != SafetySeverity.LIMIT:
                continue
            next_speed = self._apply_speed_constraint(speed, constraint)
            if next_speed != speed:
                limiting_constraints.append(constraint)
                speed = next_speed

        command = ActuatorCommand(
            source=selected.source,
            linear_speed_mps=speed,
            steering_angle_rad=steering,
            selected_monotonic_ns=now,
            command_id=selected.command_id,
            reason=(
                self._constraint_reason(tuple(limiting_constraints))
                if limiting_constraints
                else None
            ),
        )
        return ArbitrationResult(
            command=command,
            selected_intent=selected,
            active_constraints=active_constraints,
            limiting_constraint_ids=tuple(
                constraint.constraint_id for constraint in limiting_constraints
            ),
        )

    def _select_intent(
        self, mode: RobotMode, mode_generation: int, now: int
    ) -> Optional[MotionIntent]:
        eligible = ELIGIBLE_SOURCES[mode]
        candidates = []
        for source, intent in list(self._latest_intents.items()):
            if intent.expires_monotonic_ns <= now:
                self._latest_intents.pop(source, None)
                continue
            if intent.mode_generation == mode_generation and source in eligible:
                candidates.append(intent)
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: (
                item.priority,
                item.sequence,
                item.created_monotonic_ns,
                item.command_id,
            ),
        )

    def _clamp_speed(self, speed: float) -> float:
        return self._clamp(
            speed,
            -self.limits.max_reverse_speed_mps,
            self.limits.max_forward_speed_mps,
        )

    @staticmethod
    def _apply_speed_constraint(speed: float, constraint: SafetyConstraint) -> float:
        if speed > 0 and constraint.max_forward_speed_mps is not None:
            return min(speed, constraint.max_forward_speed_mps)
        if speed < 0 and constraint.max_reverse_speed_mps is not None:
            return max(speed, -constraint.max_reverse_speed_mps)
        return speed

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _constraint_reason(constraints: Tuple[SafetyConstraint, ...]) -> str:
        return "; ".join(
            constraint.reason or constraint.constraint_id for constraint in constraints
        )

    @staticmethod
    def _reject(
        intent: MotionIntent, reason: IntentRejectionReason
    ) -> IntentSubmissionResult:
        return IntentSubmissionResult(
            intent=intent,
            accepted=False,
            rejection_reason=reason,
        )

    @staticmethod
    def _stop_result(
        now: int,
        selected: Optional[MotionIntent],
        active_constraints: Tuple[SafetyConstraint, ...],
        *,
        reason: str,
        limiting_constraints: Tuple[SafetyConstraint, ...] = (),
        source: MotionSource = MotionSource.IDLE,
    ) -> ArbitrationResult:
        return ArbitrationResult(
            command=ActuatorCommand(
                source=source,
                linear_speed_mps=0.0,
                steering_angle_rad=0.0,
                selected_monotonic_ns=now,
                command_id=selected.command_id if selected else None,
                reason=reason,
            ),
            selected_intent=selected,
            active_constraints=active_constraints,
            limiting_constraint_ids=tuple(
                constraint.constraint_id for constraint in limiting_constraints
            ),
        )


__all__ = ["MotionArbiter"]
