"""Translation and serialized application of physical motion commands."""

import math
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

from app.services.autonomy.messages import ActuatorCommand


class DriveDirection(str, Enum):
    """Direction understood by the existing motor adapter."""

    STOPPED = "stopped"
    FORWARD = "forward"
    REVERSE = "reverse"


class DriveHardware(Protocol):
    """Narrow boundary implemented by :class:`PicarxAdapter`."""

    def forward(self, speed: int) -> None: ...

    def backward(self, speed: int) -> None: ...

    def stop(self) -> None: ...

    def set_dir_servo_angle(self, value: float) -> None: ...


class VirtualDriveHardware:
    """In-memory drive sink used while coherent simulation owns motion."""

    def __init__(self) -> None:
        self.direction = DriveDirection.STOPPED
        self.speed = 0
        self.steering_angle_deg = 0.0

    def forward(self, speed: int) -> None:
        self.direction = DriveDirection.FORWARD
        self.speed = speed

    def backward(self, speed: int) -> None:
        self.direction = DriveDirection.REVERSE
        self.speed = speed

    def stop(self) -> None:
        self.direction = DriveDirection.STOPPED
        self.speed = 0

    def set_dir_servo_angle(self, value: float) -> None:
        self.steering_angle_deg = value


class SelectableDriveHardware:
    """Atomically route drive writes to physical hardware or a virtual sink."""

    def __init__(
        self,
        physical: DriveHardware,
        virtual: DriveHardware,
        *,
        simulation_enabled: bool = False,
    ) -> None:
        self._physical = physical
        self._virtual = virtual
        self._simulation_enabled = simulation_enabled
        self._lock = threading.RLock()

    @property
    def simulation_enabled(self) -> bool:
        with self._lock:
            return self._simulation_enabled

    def set_simulation_enabled(self, enabled: bool) -> None:
        """Stop both sides around a route change; never transfer motion state."""

        with self._lock:
            if enabled == self._simulation_enabled:
                return
            self._active.stop()
            self._simulation_enabled = enabled
            self._active.stop()

    def forward(self, speed: int) -> None:
        with self._lock:
            self._active.forward(speed)

    def backward(self, speed: int) -> None:
        with self._lock:
            self._active.backward(speed)

    def stop(self) -> None:
        with self._lock:
            self._active.stop()

    def set_dir_servo_angle(self, value: float) -> None:
        with self._lock:
            self._active.set_dir_servo_angle(value)

    @property
    def _active(self) -> DriveHardware:
        return self._virtual if self._simulation_enabled else self._physical


@dataclass(frozen=True)
class ActuationCalibration:
    """Explicit mapping between SI motion and existing hardware units."""

    max_forward_speed_mps: float
    max_reverse_speed_mps: float
    max_abs_steering_angle_rad: float
    max_forward_command: int = 100
    max_reverse_command: int = 100
    steering_angle_sign: int = 1

    def __post_init__(self) -> None:
        for name, value in [
            ("max_forward_speed_mps", self.max_forward_speed_mps),
            ("max_reverse_speed_mps", self.max_reverse_speed_mps),
            ("max_abs_steering_angle_rad", self.max_abs_steering_angle_rad),
        ]:
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and greater than zero")
        for name, value in [
            ("max_forward_command", self.max_forward_command),
            ("max_reverse_command", self.max_reverse_command),
        ]:
            if not 1 <= value <= 100:
                raise ValueError(f"{name} must be between 1 and 100")
        if self.steering_angle_sign not in (-1, 1):
            raise ValueError("steering_angle_sign must be -1 or 1")


@dataclass(frozen=True)
class HardwareMotionCommand:
    """A command expressed in the units accepted by the current adapter."""

    direction: DriveDirection
    speed: int
    steering_angle_deg: float

    def __post_init__(self) -> None:
        if not 0 <= self.speed <= 100:
            raise ValueError("speed must be between 0 and 100")
        if self.direction == DriveDirection.STOPPED and self.speed != 0:
            raise ValueError("a stopped command must have zero speed")
        if self.direction != DriveDirection.STOPPED and self.speed == 0:
            raise ValueError("a moving command must have non-zero speed")
        if not math.isfinite(self.steering_angle_deg):
            raise ValueError("steering_angle_deg must be finite")


class LinearActuatorTranslator:
    """Clamp and linearly map SI commands to motor percentage and servo degrees."""

    def __init__(self, calibration: ActuationCalibration) -> None:
        self.calibration = calibration

    def translate(self, command: ActuatorCommand) -> HardwareMotionCommand:
        """Translate a resolved command without inventing physical calibration."""

        steering = self._clamp(
            command.steering_angle_rad,
            -self.calibration.max_abs_steering_angle_rad,
            self.calibration.max_abs_steering_angle_rad,
        )
        steering_degrees = math.degrees(steering) * self.calibration.steering_angle_sign

        if command.linear_speed_mps == 0:
            return HardwareMotionCommand(
                direction=DriveDirection.STOPPED,
                speed=0,
                steering_angle_deg=steering_degrees,
            )

        if command.linear_speed_mps > 0:
            speed = self._scale_speed(
                command.linear_speed_mps,
                self.calibration.max_forward_speed_mps,
                self.calibration.max_forward_command,
            )
            direction = DriveDirection.FORWARD
        else:
            speed = self._scale_speed(
                -command.linear_speed_mps,
                self.calibration.max_reverse_speed_mps,
                self.calibration.max_reverse_command,
            )
            direction = DriveDirection.REVERSE

        if speed == 0:
            direction = DriveDirection.STOPPED
        return HardwareMotionCommand(
            direction=direction,
            speed=speed,
            steering_angle_deg=steering_degrees,
        )

    @staticmethod
    def _scale_speed(speed: float, physical_max: float, command_max: int) -> int:
        ratio = LinearActuatorTranslator._clamp(speed / physical_max, 0.0, 1.0)
        return int(round(ratio * command_max))

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))


class HardwareController:
    """The intended sole writer for drive motors and the steering servo."""

    def __init__(
        self,
        hardware: DriveHardware,
        translator: LinearActuatorTranslator,
    ) -> None:
        self._hardware = hardware
        self._translator = translator
        self._last_command: Optional[HardwareMotionCommand] = None
        self._write_lock = threading.Lock()

    @property
    def last_command(self) -> Optional[HardwareMotionCommand]:
        return self._last_command

    def apply(self, command: ActuatorCommand) -> HardwareMotionCommand:
        """Apply one command, stopping first on reversal and on write failure."""

        with self._write_lock:
            translated = self._translator.translate(command)
            previous = self._last_command
            if translated == previous:
                return translated

            try:
                if (
                    previous is None
                    or translated.steering_angle_deg != previous.steering_angle_deg
                ):
                    self._hardware.set_dir_servo_angle(translated.steering_angle_deg)

                if self._requires_stop_before_direction_change(previous, translated):
                    self._hardware.stop()

                if translated.direction == DriveDirection.FORWARD:
                    self._hardware.forward(translated.speed)
                elif translated.direction == DriveDirection.REVERSE:
                    self._hardware.backward(translated.speed)
                else:
                    self._hardware.stop()
            except Exception:
                self._best_effort_stop()
                self._last_command = None
                raise

            self._last_command = translated
            return translated

    def force_stop(self) -> None:
        """Write a stop even if the cached state already appears stopped."""

        with self._write_lock:
            self._hardware.stop()
            self._last_command = HardwareMotionCommand(
                direction=DriveDirection.STOPPED,
                speed=0,
                steering_angle_deg=(
                    self._last_command.steering_angle_deg if self._last_command else 0.0
                ),
            )

    def _best_effort_stop(self) -> None:
        try:
            self._hardware.stop()
        except Exception:
            pass

    @staticmethod
    def _requires_stop_before_direction_change(
        previous: Optional[HardwareMotionCommand],
        current: HardwareMotionCommand,
    ) -> bool:
        if previous is None:
            return False
        moving_directions = {DriveDirection.FORWARD, DriveDirection.REVERSE}
        return (
            previous.direction in moving_directions
            and current.direction in moving_directions
            and previous.direction != current.direction
        )


__all__ = [
    "ActuationCalibration",
    "DriveDirection",
    "DriveHardware",
    "HardwareController",
    "HardwareMotionCommand",
    "LinearActuatorTranslator",
    "SelectableDriveHardware",
    "VirtualDriveHardware",
]
