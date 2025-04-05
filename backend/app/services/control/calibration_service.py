import asyncio
from typing import TYPE_CHECKING, Any, Dict

from app.core.px_logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.schemas.config import ConfigSchema
from robot_hat import constrain
from robot_hat.motor.config import MotorDirection

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.managers.file_management.json_data_manager import JsonDataManager
    from robot_hat import Motor, ServoService


class CalibrationService(metaclass=SingletonMeta):
    MAX_SERVO_ANGLE_OFFSET = 20
    MIN_SERVO_ANGLE_OFFSET = -20

    def __init__(
        self,
        picarx: "PicarxAdapter",
        config_manager: "JsonDataManager",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.logger = Logger(__name__, app_name="px_robot")
        self.px = picarx
        self.config_manager = config_manager
        self.step = 0.1
        self.config = ConfigSchema(**self.config_manager.load_data())

    def _reset_calibration(self) -> Dict[str, Any]:
        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            servo.reset_calibration()
        self.px.motor_controller.reset_calibration()
        return self.get_current_config()

    async def reset_calibration(self) -> Dict[str, Any]:
        await asyncio.to_thread(self._reset_calibration)
        return self.get_current_config()

    async def _update_servo_angle(self, servo: "ServoService", value: float) -> None:
        await asyncio.to_thread(
            servo.update_calibration,
            round(
                constrain(
                    value, self.MIN_SERVO_ANGLE_OFFSET, self.MAX_SERVO_ANGLE_OFFSET
                ),
                2,
            ),
        )

    async def _increase_servo_angle(self, servo: "ServoService") -> None:
        await self._update_servo_angle(
            servo,
            servo.calibration_offset + self.step,
        )

    async def _decrease_servo_angle(self, servo: "ServoService") -> None:
        await self._update_servo_angle(
            servo,
            servo.calibration_offset - self.step,
        )

    async def update_servo_dir_angle(self, value: float) -> Dict[str, Any]:
        await self._update_servo_angle(self.px.steering_servo, value)
        return self.get_current_config()

    async def update_cam_pan_angle(self, value: float) -> Dict[str, Any]:
        await self._update_servo_angle(self.px.cam_pan_servo, value)
        return self.get_current_config()

    async def update_cam_tilt_angle(self, value: float) -> Dict[str, Any]:
        await self._update_servo_angle(self.px.cam_tilt_servo, value)
        return self.get_current_config()

    async def increase_servo_dir_angle(self) -> Dict[str, Any]:
        await self._increase_servo_angle(self.px.steering_servo)
        return self.get_current_config()

    async def decrease_servo_dir_angle(self) -> Dict[str, Any]:
        await self._decrease_servo_angle(self.px.steering_servo)
        return self.get_current_config()

    async def increase_cam_pan_angle(self) -> Dict[str, Any]:
        await self._increase_servo_angle(self.px.cam_pan_servo)
        return self.get_current_config()

    async def decrease_cam_pan_angle(self) -> Dict[str, Any]:
        await self._decrease_servo_angle(self.px.cam_pan_servo)
        return self.get_current_config()

    async def increase_cam_tilt_angle(self) -> Dict[str, Any]:
        await self._increase_servo_angle(self.px.cam_tilt_servo)
        return self.get_current_config()

    async def decrease_cam_tilt_angle(self) -> Dict[str, Any]:
        await self._decrease_servo_angle(self.px.cam_tilt_servo)
        return self.get_current_config()

    def _reverse_motor(self, motor: "Motor") -> Dict[str, Any]:
        motor.update_calibration_direction(-motor.direction)
        return self.get_current_config()

    def reverse_left_motor(self) -> Dict[str, Any]:
        return self._reverse_motor(self.px.motor_controller.left_motor)

    def _update_motor(self, motor: "Motor", value: MotorDirection) -> Dict[str, Any]:
        motor.update_calibration_direction(value)
        return self.get_current_config()

    def update_left_motor_direction(self, value: MotorDirection) -> Dict[str, Any]:
        return self._update_motor(self.px.motor_controller.left_motor, value)

    def update_right_motor_direction(self, value: MotorDirection) -> Dict[str, Any]:
        return self._update_motor(self.px.motor_controller.right_motor, value)

    def save_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.config = ConfigSchema(**data)
        steering_servo_offset = self.px.steering_servo.calibration_offset
        cam_pan_servo_offset = self.px.cam_pan_servo.calibration_offset
        cam_tilt_servo_offset = self.px.cam_tilt_servo.calibration_offset
        left_motor_direction = self.px.motor_controller.left_motor.direction
        right_motor_direction = self.px.motor_controller.right_motor.direction

        self.config.steering_servo.calibration_offset = steering_servo_offset
        self.config.cam_pan_servo.calibration_offset = cam_pan_servo_offset
        self.config.cam_tilt_servo.calibration_offset = cam_tilt_servo_offset
        self.config.left_motor.calibration_direction = left_motor_direction
        self.config.right_motor.calibration_direction = right_motor_direction
        return self.save_calibration()

    def reverse_right_motor(self) -> Dict[str, Any]:
        return self._reverse_motor(self.px.motor_controller.right_motor)

    def get_current_config(self) -> Dict[str, Any]:
        steering_servo_offset = self.px.steering_servo.calibration_offset
        cam_pan_servo_offset = self.px.cam_pan_servo.calibration_offset
        cam_tilt_servo_offset = self.px.cam_tilt_servo.calibration_offset
        left_motor_direction = self.px.motor_controller.left_motor.direction
        right_motor_direction = self.px.motor_controller.right_motor.direction

        self.config.steering_servo.calibration_offset = steering_servo_offset
        self.config.cam_pan_servo.calibration_offset = cam_pan_servo_offset
        self.config.cam_tilt_servo.calibration_offset = cam_tilt_servo_offset
        self.config.left_motor.calibration_direction = left_motor_direction
        self.config.right_motor.calibration_direction = right_motor_direction

        data = self.config.model_dump(mode="json")

        return data

    def save_calibration(self) -> Dict[str, Any]:
        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            servo.update_calibration(servo.calibration_offset, True)

        left_motor_direction = self.px.motor_controller.left_motor.direction
        right_motor_direction = self.px.motor_controller.right_motor.direction

        self.px.motor_controller.update_left_motor_calibration_direction(
            left_motor_direction, True
        )
        self.px.motor_controller.update_right_motor_calibration_direction(
            right_motor_direction, True
        )
        config = self.get_current_config()

        self.config_manager.update(config)
        self.config = ConfigSchema(**config)
        self.px.config = self.config

        return config
