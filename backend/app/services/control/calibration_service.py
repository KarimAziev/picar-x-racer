from typing import TYPE_CHECKING, Any, Dict, Optional

from app.core.px_logger import Logger
from robot_hat import constrain
from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.interfaces.motor_abc import MotorABC

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.services.control.settings_service import SettingsService
    from robot_hat import ServoService

_log = Logger(__name__, app_name="px_robot")


class CalibrationService:
    MAX_SERVO_ANGLE_OFFSET = 180
    MIN_SERVO_ANGLE_OFFSET = -180

    def __init__(
        self,
        picarx: "PicarxAdapter",
        settings_service: "SettingsService",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.px = picarx
        self.step = 0.1
        self.settings_service = settings_service

    def reset_calibration(self) -> Dict[str, Any]:
        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            if servo:
                servo.reset_calibration()
        if self.px.motor_controller:
            self.px.motor_controller.reset_calibration()
        return self.current_calibration_settings()

    def _update_servo_angle(self, servo: "ServoService", value: float) -> None:
        servo.update_calibration(
            round(
                constrain(
                    value, self.MIN_SERVO_ANGLE_OFFSET, self.MAX_SERVO_ANGLE_OFFSET
                ),
                2,
            )
        )

    def _increase_servo_angle(self, servo: "ServoService") -> None:
        self._update_servo_angle(
            servo,
            servo.calibration_offset + self.step,
        )

    def _decrease_servo_angle(self, servo: "ServoService") -> None:
        self._update_servo_angle(
            servo,
            servo.calibration_offset - self.step,
        )

    def update_servo_dir_angle(self, value: float) -> Dict[str, Any]:
        if self.px.steering_servo:
            self._update_servo_angle(self.px.steering_servo, value)
        return self.current_calibration_settings()

    def update_cam_pan_angle(self, value: float) -> Dict[str, Any]:
        if self.px.cam_pan_servo:
            self._update_servo_angle(self.px.cam_pan_servo, value)
        return self.current_calibration_settings()

    def update_cam_tilt_angle(self, value: float) -> Dict[str, Any]:
        if self.px.cam_tilt_servo:
            self._update_servo_angle(self.px.cam_tilt_servo, value)
        return self.current_calibration_settings()

    def increase_servo_dir_angle(self) -> Dict[str, Any]:
        if self.px.steering_servo:
            self._increase_servo_angle(self.px.steering_servo)
        return self.current_calibration_settings()

    def decrease_servo_dir_angle(self) -> Dict[str, Any]:
        if self.px.steering_servo:
            self._decrease_servo_angle(self.px.steering_servo)
        return self.current_calibration_settings()

    def increase_cam_pan_angle(self) -> Dict[str, Any]:
        if self.px.cam_pan_servo:
            self._increase_servo_angle(self.px.cam_pan_servo)
        return self.current_calibration_settings()

    def decrease_cam_pan_angle(self) -> Dict[str, Any]:
        if self.px.cam_pan_servo:
            self._decrease_servo_angle(self.px.cam_pan_servo)
        return self.current_calibration_settings()

    def increase_cam_tilt_angle(self) -> Dict[str, Any]:
        if self.px.cam_tilt_servo:
            self._increase_servo_angle(self.px.cam_tilt_servo)
        return self.current_calibration_settings()

    def decrease_cam_tilt_angle(self) -> Dict[str, Any]:
        if self.px.cam_tilt_servo:
            self._decrease_servo_angle(self.px.cam_tilt_servo)
        return self.current_calibration_settings()

    def _reverse_motor(self, motor: Optional[MotorABC]) -> Dict[str, Any]:
        if not motor:
            raise ValueError("No motor")
        _log.info(
            "Updating motor direction from %s to %s", motor.direction, -motor.direction
        )
        motor.update_calibration_direction(-motor.direction)
        _log.info("Updated motor direction %s", motor.direction)

        return self.current_calibration_settings()

    def _update_motor(
        self, motor: Optional[MotorABC], value: MotorDirection
    ) -> Dict[str, Any]:
        if motor:
            motor.update_calibration_direction(value)
        return self.current_calibration_settings()

    def _get_motor(self, index: int) -> MotorABC:
        if index < 0 or index >= len(self.px.motors):
            raise ValueError(f"Motor {index + 1} is not configured")
        return self.px.motors[index]

    def reverse_motor(self, index: int) -> Dict[str, Any]:
        return self._reverse_motor(self._get_motor(index))

    def update_motor_direction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        index = int(data["index"])
        value = data["value"]
        if value not in (-1, 1):
            raise ValueError("Motor direction must be either 1 or -1")
        return self._update_motor(self._get_motor(index), value)

    def save_calibration(self) -> Dict[str, Any]:
        _log.info("Saving current calibration settings")
        settings = self.settings_service.get_current_settings()
        updated = self.settings_service.save_settings(settings)
        return updated.model_dump(mode="json")

    def current_calibration_settings(self) -> Dict[str, Any]:
        data_map: Dict[str, Any] = {}

        for servo_name in [
            "steering_servo",
            "cam_tilt_servo",
            "cam_pan_servo",
        ]:
            servo: Optional["ServoService"] = getattr(self.px, servo_name)

            if servo is not None:
                data_map[servo_name] = {"calibration_offset": servo.calibration_offset}

        data_map["motors"] = [
            {"calibration_direction": motor.direction} for motor in self.px.motors
        ]

        _log.info("Calibration settings %s", data_map)

        return data_map
