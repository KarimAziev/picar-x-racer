import asyncio
from typing import TYPE_CHECKING, Any, Dict

from app.schemas.config import ConfigSchema
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from robot_hat import constrain

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.services.car_control.config_service import ConfigService
    from robot_hat import Motor, ServoService


class CalibrationService(metaclass=SingletonMeta):
    def __init__(
        self,
        picarx: "PicarxAdapter",
        config_manager: "ConfigService",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.logger = Logger(__name__)
        self.px = picarx
        self.config_manager = config_manager
        self.step = 0.1

    def _reset_calibration(self) -> Dict[str, Any]:
        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            servo.reset_calibration()
        self.px.motor_controller.reset_calibration()
        return self.get_calibration_data()

    async def reset_calibration(self) -> Dict[str, Any]:
        await asyncio.to_thread(self._reset_calibration)
        return self.get_calibration_data()

    async def _increase_servo_angle(self, servo: "ServoService") -> None:
        await asyncio.to_thread(
            servo.update_calibration,
            round(constrain(servo.calibration_offset + self.step, -20, 20), 2),
        )

    async def _decrease_servo_angle(self, servo: "ServoService") -> None:
        await asyncio.to_thread(
            servo.update_calibration,
            round(constrain(servo.calibration_offset - self.step, -20, 20), 2),
        )

    async def increase_servo_dir_angle(self) -> Dict[str, Any]:
        await self._increase_servo_angle(self.px.steering_servo)
        return self.get_calibration_data()

    async def decrease_servo_dir_angle(self) -> Dict[str, Any]:
        await self._decrease_servo_angle(self.px.steering_servo)
        return self.get_calibration_data()

    async def increase_cam_pan_angle(self) -> Dict[str, Any]:
        await self._increase_servo_angle(self.px.cam_pan_servo)
        return self.get_calibration_data()

    async def decrease_cam_pan_angle(self) -> Dict[str, Any]:
        await self._decrease_servo_angle(self.px.cam_pan_servo)
        return self.get_calibration_data()

    async def increase_cam_tilt_angle(self) -> Dict[str, Any]:
        await self._increase_servo_angle(self.px.cam_tilt_servo)
        return self.get_calibration_data()

    async def decrease_cam_tilt_angle(self) -> Dict[str, Any]:
        await self._decrease_servo_angle(self.px.cam_tilt_servo)
        return self.get_calibration_data()

    def _reverse_motor(self, motor: "Motor") -> Dict[str, Any]:
        motor.update_calibration_direction(-motor.direction)
        return self.get_calibration_data()

    def reverse_left_motor(self) -> Dict[str, Any]:
        return self._reverse_motor(self.px.motor_controller.left_motor)

    def reverse_right_motor(self) -> Dict[str, Any]:
        return self._reverse_motor(self.px.motor_controller.right_motor)

    async def save_calibration(self) -> Dict[str, Any]:
        config = ConfigSchema(**self.config_manager.load_settings())
        steering_servo_offset = self.px.steering_servo.calibration_offset
        cam_pan_servo_offset = self.px.cam_pan_servo.calibration_offset
        cam_tilt_servo_offset = self.px.cam_tilt_servo.calibration_offset
        left_motor = self.px.motor_controller.left_motor.direction
        right_motor = self.px.motor_controller.right_motor.direction

        config.steering_servo.calibration_offset = steering_servo_offset
        config.cam_pan_servo.calibration_offset = cam_pan_servo_offset
        config.cam_tilt_servo.calibration_offset = cam_tilt_servo_offset
        config.left_motor.calibration_direction = left_motor
        config.right_motor.calibration_direction = right_motor

        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            servo.update_calibration(servo.calibration_offset, True)

        self.px.motor_controller.update_left_motor_calibration_direction(
            left_motor, True
        )
        self.px.motor_controller.update_right_motor_calibration_direction(
            right_motor, True
        )

        self.config_manager.save_settings(config.model_dump(mode="json"))
        self.px.config = config

        return self.get_calibration_data()

    def get_calibration_data(self) -> Dict[str, Any]:
        return {
            "steering_servo_offset": self.px.steering_servo.calibration_offset,
            "cam_pan_servo_offset": self.px.cam_pan_servo.calibration_offset,
            "cam_tilt_servo_offset": self.px.cam_tilt_servo.calibration_offset,
            "left_motor_direction": self.px.motor_controller.left_motor.direction,
            "right_motor_direction": self.px.motor_controller.right_motor.direction,
        }
