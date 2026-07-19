import math
import unittest
from typing import List, Tuple, Union

from app.services.autonomy import (
    ActuationCalibration,
    ActuatorCommand,
    DriveDirection,
    HardwareController,
    LinearActuatorTranslator,
    MotionSource,
)
from app.schemas.robot.motion_control import MotionControlConfig
from pydantic import ValidationError


HardwareCall = Tuple[str, Union[int, float, None]]


class FakeDriveHardware:
    def __init__(self) -> None:
        self.calls: List[HardwareCall] = []
        self.fail_on: str | None = None

    def forward(self, speed: int) -> None:
        self._record("forward", speed)

    def backward(self, speed: int) -> None:
        self._record("backward", speed)

    def stop(self) -> None:
        self._record("stop", None)

    def set_dir_servo_angle(self, value: float) -> None:
        self._record("steer", value)

    def _record(self, operation: str, value: Union[int, float, None]) -> None:
        self.calls.append((operation, value))
        if operation == self.fail_on:
            raise OSError(f"{operation} failed")


class ActuationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = ActuationCalibration(
            max_forward_speed_mps=1.0,
            max_reverse_speed_mps=0.5,
            max_abs_steering_angle_rad=math.pi / 4,
            max_forward_command=80,
            max_reverse_command=60,
        )
        self.translator = LinearActuatorTranslator(self.calibration)
        self.hardware = FakeDriveHardware()
        self.controller = HardwareController(self.hardware, self.translator)

    @staticmethod
    def command(speed: float, steering: float = 0.0) -> ActuatorCommand:
        return ActuatorCommand(
            source=MotionSource.MANUAL,
            linear_speed_mps=speed,
            steering_angle_rad=steering,
            selected_monotonic_ns=1,
            command_id="test-command",
        )


class TestActuationCalibration(ActuationTestCase):
    def test_rejects_missing_or_invalid_physical_calibration(self) -> None:
        for value in [0.0, -1.0, math.inf, math.nan]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ActuationCalibration(
                        max_forward_speed_mps=value,
                        max_reverse_speed_mps=0.5,
                        max_abs_steering_angle_rad=0.5,
                    )

    def test_motion_runtime_requires_speed_calibration_when_enabled(self) -> None:
        with self.assertRaisesRegex(ValidationError, "speeds are required"):
            MotionControlConfig(enabled=True)

        disabled = MotionControlConfig(enabled=False)
        self.assertIsNone(disabled.max_forward_speed_mps)
        self.assertIsNone(disabled.max_reverse_speed_mps)

    def test_command_timeout_covers_two_control_cycles(self) -> None:
        with self.assertRaisesRegex(ValidationError, "at least two"):
            MotionControlConfig(
                enabled=True,
                control_frequency_hz=5,
                command_timeout_ms=250,
                max_forward_speed_mps=1.0,
                max_reverse_speed_mps=0.5,
            )

    def test_rejects_hardware_commands_outside_adapter_range(self) -> None:
        for value in [0, 101]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "between 1 and 100"):
                    ActuationCalibration(
                        max_forward_speed_mps=1.0,
                        max_reverse_speed_mps=0.5,
                        max_abs_steering_angle_rad=0.5,
                        max_forward_command=value,
                    )


class TestLinearActuatorTranslator(ActuationTestCase):
    def test_maps_forward_and_reverse_against_separate_calibrations(self) -> None:
        forward = self.translator.translate(self.command(0.5))
        reverse = self.translator.translate(self.command(-0.25))

        self.assertEqual(forward.direction, DriveDirection.FORWARD)
        self.assertEqual(forward.speed, 40)
        self.assertEqual(reverse.direction, DriveDirection.REVERSE)
        self.assertEqual(reverse.speed, 30)

    def test_clamps_speed_and_steering_to_calibrated_maximum(self) -> None:
        translated = self.translator.translate(self.command(2.0, math.pi / 2))

        self.assertEqual(translated.speed, 80)
        self.assertAlmostEqual(translated.steering_angle_deg, 45.0)

    def test_zero_and_sub_resolution_speed_translate_to_stop(self) -> None:
        zero = self.translator.translate(self.command(0.0, 0.1))
        sub_resolution = self.translator.translate(self.command(0.001))

        self.assertEqual(zero.direction, DriveDirection.STOPPED)
        self.assertEqual(zero.speed, 0)
        self.assertEqual(sub_resolution.direction, DriveDirection.STOPPED)
        self.assertEqual(sub_resolution.speed, 0)


class TestHardwareController(ActuationTestCase):
    def test_applies_steering_before_forward_motion(self) -> None:
        translated = self.controller.apply(self.command(0.5, math.pi / 6))

        self.assertEqual(
            self.hardware.calls,
            [("steer", 29.999999999999996), ("forward", 40)],
        )
        self.assertEqual(self.controller.last_command, translated)

    def test_stops_before_reversing_direction(self) -> None:
        self.controller.apply(self.command(0.5))
        self.hardware.calls.clear()

        self.controller.apply(self.command(-0.25))

        self.assertEqual(self.hardware.calls, [("stop", None), ("backward", 30)])

    def test_does_not_repeat_identical_hardware_writes(self) -> None:
        command = self.command(0.5, 0.2)
        self.controller.apply(command)
        self.hardware.calls.clear()

        self.controller.apply(command)

        self.assertEqual(self.hardware.calls, [])

    def test_stop_is_written_when_previous_command_was_moving(self) -> None:
        self.controller.apply(self.command(0.5))
        self.hardware.calls.clear()

        self.controller.apply(self.command(0.0))

        self.assertEqual(self.hardware.calls, [("stop", None)])

    def test_direction_write_failure_attempts_stop_and_clears_cached_state(
        self,
    ) -> None:
        self.hardware.fail_on = "forward"

        with self.assertRaisesRegex(OSError, "forward failed"):
            self.controller.apply(self.command(0.5))

        self.assertEqual(
            self.hardware.calls,
            [("steer", 0.0), ("forward", 40), ("stop", None)],
        )
        self.assertIsNone(self.controller.last_command)

    def test_force_stop_bypasses_cached_state(self) -> None:
        self.controller.apply(self.command(0.0))
        self.hardware.calls.clear()

        self.controller.force_stop()

        self.assertEqual(self.hardware.calls, [("stop", None)])


if __name__ == "__main__":
    unittest.main()
