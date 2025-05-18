import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from app.core.px_logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.schemas.config import (
    AngularServoConfig,
    GPIOAngularServoConfig,
    GPIODCMotorConfig,
    HardwareConfig,
    I2CDCMotorConfig,
)
from robot_hat import constrain
from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.interfaces.motor_abc import MotorABC

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.managers.file_management.json_data_manager import JsonDataManager
    from robot_hat import ServoService


class CalibrationService(metaclass=SingletonMeta):
    MAX_SERVO_ANGLE_OFFSET = 90
    MIN_SERVO_ANGLE_OFFSET = -90

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
        self.config = HardwareConfig(**self.config_manager.load_data())

    def _reset_calibration(self) -> Dict[str, Any]:
        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            if servo:
                servo.reset_calibration()
        if self.px.motor_controller:
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
        if self.px.steering_servo:
            await self._update_servo_angle(self.px.steering_servo, value)
        return self.get_current_config()

    async def update_cam_pan_angle(self, value: float) -> Dict[str, Any]:
        if self.px.cam_pan_servo:
            await self._update_servo_angle(self.px.cam_pan_servo, value)
        return self.get_current_config()

    async def update_cam_tilt_angle(self, value: float) -> Dict[str, Any]:
        if self.px.cam_tilt_servo:
            await self._update_servo_angle(self.px.cam_tilt_servo, value)
        return self.get_current_config()

    async def increase_servo_dir_angle(self) -> Dict[str, Any]:
        if self.px.steering_servo:
            await self._increase_servo_angle(self.px.steering_servo)
        return self.get_current_config()

    async def decrease_servo_dir_angle(self) -> Dict[str, Any]:
        if self.px.steering_servo:
            await self._decrease_servo_angle(self.px.steering_servo)
        return self.get_current_config()

    async def increase_cam_pan_angle(self) -> Dict[str, Any]:
        if self.px.cam_pan_servo:
            await self._increase_servo_angle(self.px.cam_pan_servo)
        return self.get_current_config()

    async def decrease_cam_pan_angle(self) -> Dict[str, Any]:
        if self.px.cam_pan_servo:
            await self._decrease_servo_angle(self.px.cam_pan_servo)
        return self.get_current_config()

    async def increase_cam_tilt_angle(self) -> Dict[str, Any]:
        if self.px.cam_tilt_servo:
            await self._increase_servo_angle(self.px.cam_tilt_servo)
        return self.get_current_config()

    async def decrease_cam_tilt_angle(self) -> Dict[str, Any]:
        if self.px.cam_tilt_servo:
            await self._decrease_servo_angle(self.px.cam_tilt_servo)
        return self.get_current_config()

    def _reverse_motor(self, motor: Optional[MotorABC]) -> Dict[str, Any]:
        if motor:
            motor.update_calibration_direction(-motor.direction)
        return self.get_current_config()

    def reverse_left_motor(self) -> Dict[str, Any]:
        if self.px.motor_controller:
            return self._reverse_motor(self.px.motor_controller.left_motor)
        return self.get_current_config()

    def _update_motor(
        self, motor: Optional[MotorABC], value: MotorDirection
    ) -> Dict[str, Any]:
        if motor:
            motor.update_calibration_direction(value)
        return self.get_current_config()

    def update_left_motor_direction(self, value: MotorDirection) -> Dict[str, Any]:
        if not self.px.motor_controller:
            return self.get_current_config()
        return self._update_motor(self.px.motor_controller.left_motor, value)

    def update_right_motor_direction(self, value: MotorDirection) -> Dict[str, Any]:
        if not self.px.motor_controller:
            return self.get_current_config()
        return self._update_motor(self.px.motor_controller.right_motor, value)

    def _sync_config(self) -> None:

        for servo_name in [
            "steering_servo",
            "cam_tilt_servo",
            "cam_pan_servo",
        ]:
            servo: "ServoService" = getattr(self.px, servo_name)
            servo_config: Union[GPIOAngularServoConfig, AngularServoConfig, None] = (
                getattr(self.config, servo_name)
            )

            if servo and servo_config:
                servo_config.calibration_offset = servo.calibration_offset

        if self.px.motor_controller:
            for motor_name in [
                "left_motor",
                "right_motor",
            ]:
                motor: Optional["MotorABC"] = getattr(self.px, motor_name)
                self.config.left_motor
                motor_config: Union[GPIODCMotorConfig, I2CDCMotorConfig, None] = (
                    getattr(self.config, motor_name)
                )
                if motor and motor_config:
                    motor_config.calibration_direction = motor.direction

    def save_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Saving config: %s", data)
        self.config = HardwareConfig(**data)
        self._sync_config()

        return self.save_calibration()

    def reverse_right_motor(self) -> Dict[str, Any]:
        if self.px.motor_controller:
            return self._reverse_motor(self.px.motor_controller.right_motor)
        return self.get_current_config()

    def get_current_config(self) -> Dict[str, Any]:
        self._sync_config()

        data = self.config.model_dump(mode="json")

        return data

    def save_calibration(self) -> Dict[str, Any]:
        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            if servo:
                servo.update_calibration(servo.calibration_offset, True)

        if self.px.left_motor:
            self.px.left_motor.update_calibration_direction(
                self.px.left_motor.direction, True
            )

        if self.px.right_motor:
            self.px.right_motor.update_calibration_direction(
                self.px.right_motor.direction, True
            )

        config = self.get_current_config()

        self.config_manager.update(config)
        self.config = HardwareConfig(**config)
        self.px.config = self.config
        self.px.cleanup()
        self.px.init_hardware()

        return config
