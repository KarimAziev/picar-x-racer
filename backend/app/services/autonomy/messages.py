"""Hardware-independent messages for motion selection and safety limiting."""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class RobotMode(str, Enum):
    """Mutually exclusive operating modes that determine command eligibility."""

    DISARMED = "disarmed"
    MANUAL = "manual"
    AUTONOMOUS = "autonomous"
    CALIBRATION = "calibration"
    ESTOP = "estop"
    FAULT = "fault"


class MotionSource(str, Enum):
    """Logical source of a motion intent or resolved actuator command."""

    MANUAL = "manual"
    AUTONOMY = "autonomy"
    CALIBRATION = "calibration"
    SAFETY = "safety"
    IDLE = "idle"


class SafetySeverity(str, Enum):
    """Effect an active safety constraint has on selected motion."""

    LIMIT = "limit"
    STOP = "stop"
    ESTOP = "estop"


class IntentRejectionReason(str, Enum):
    """Machine-readable reason why a motion intent was rejected."""

    SOURCE_NOT_COMMANDABLE = "source_not_commandable"
    WRONG_MODE = "wrong_mode"
    WRONG_MODE_GENERATION = "wrong_mode_generation"
    CREATED_IN_FUTURE = "created_in_future"
    EXPIRED = "expired"
    STALE_SEQUENCE = "stale_sequence"


def _validate_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class MotionIntent:
    """An expiring request for physical vehicle motion in SI units."""

    command_id: str
    source: MotionSource
    sequence: int
    mode_generation: int
    linear_speed_mps: float
    steering_angle_rad: float
    created_monotonic_ns: int
    expires_monotonic_ns: int
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.command_id.strip():
            raise ValueError("command_id must not be empty")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if self.mode_generation < 0:
            raise ValueError("mode_generation must be non-negative")
        if self.created_monotonic_ns < 0:
            raise ValueError("created_monotonic_ns must be non-negative")
        if self.expires_monotonic_ns <= self.created_monotonic_ns:
            raise ValueError("expires_monotonic_ns must be after creation")
        _validate_finite("linear_speed_mps", self.linear_speed_mps)
        _validate_finite("steering_angle_rad", self.steering_angle_rad)


@dataclass(frozen=True)
class MotionLimits:
    """Absolute physical limits applied before safety-specific constraints."""

    max_forward_speed_mps: float
    max_reverse_speed_mps: float
    max_abs_steering_angle_rad: float

    def __post_init__(self) -> None:
        for name, value in [
            ("max_forward_speed_mps", self.max_forward_speed_mps),
            ("max_reverse_speed_mps", self.max_reverse_speed_mps),
            ("max_abs_steering_angle_rad", self.max_abs_steering_angle_rad),
        ]:
            _validate_finite(name, value)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class SafetyConstraint:
    """A temporary or latched restriction applied to selected vehicle motion."""

    constraint_id: str
    source: str
    severity: SafetySeverity
    created_monotonic_ns: int
    reason: str
    expires_monotonic_ns: Optional[int] = None
    max_forward_speed_mps: Optional[float] = None
    max_reverse_speed_mps: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.constraint_id.strip():
            raise ValueError("constraint_id must not be empty")
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if self.created_monotonic_ns < 0:
            raise ValueError("created_monotonic_ns must be non-negative")
        if (
            self.expires_monotonic_ns is not None
            and self.expires_monotonic_ns <= self.created_monotonic_ns
        ):
            raise ValueError("expires_monotonic_ns must be after creation")
        for name, value in [
            ("max_forward_speed_mps", self.max_forward_speed_mps),
            ("max_reverse_speed_mps", self.max_reverse_speed_mps),
        ]:
            if value is not None:
                _validate_finite(name, value)
                if value < 0:
                    raise ValueError(f"{name} must be non-negative")
        if (
            self.severity == SafetySeverity.LIMIT
            and self.max_forward_speed_mps is None
            and self.max_reverse_speed_mps is None
        ):
            raise ValueError("limit constraints must define a speed limit")


@dataclass(frozen=True)
class ActuatorCommand:
    """Final resolved command suitable for translation by a hardware controller."""

    source: MotionSource
    linear_speed_mps: float
    steering_angle_rad: float
    selected_monotonic_ns: int
    command_id: Optional[str] = None
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.selected_monotonic_ns < 0:
            raise ValueError("selected_monotonic_ns must be non-negative")
        _validate_finite("linear_speed_mps", self.linear_speed_mps)
        _validate_finite("steering_angle_rad", self.steering_angle_rad)

    @property
    def is_stop(self) -> bool:
        return self.linear_speed_mps == 0.0


@dataclass(frozen=True)
class IntentSubmissionResult:
    """Result of offering a motion intent to the arbiter."""

    intent: MotionIntent
    accepted: bool
    rejection_reason: Optional[IntentRejectionReason] = None


@dataclass(frozen=True)
class ArbitrationResult:
    """Resolved actuator command and the policy inputs that affected it."""

    command: ActuatorCommand
    selected_intent: Optional[MotionIntent]
    active_constraints: Tuple[SafetyConstraint, ...] = ()
    limiting_constraint_ids: Tuple[str, ...] = ()


__all__ = [
    "ActuatorCommand",
    "ArbitrationResult",
    "IntentRejectionReason",
    "IntentSubmissionResult",
    "MotionIntent",
    "MotionLimits",
    "MotionSource",
    "RobotMode",
    "SafetyConstraint",
    "SafetySeverity",
]
