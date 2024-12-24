from time import sleep
from typing import TYPE_CHECKING, Any, Dict

from app.schemas.config import ConfigSchema
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from robot_hat import constrain

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.services.car_control.config_service import ConfigService


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

    def servos_test(self) -> None:
        self.px.set_dir_servo_angle(-30)
        sleep(0.5)
        self.px.set_dir_servo_angle(30)
        sleep(0.5)
        self.px.set_dir_servo_angle(0)
        sleep(0.5)
        self.px.set_cam_pan_angle(-30)
        sleep(0.5)
        self.px.set_cam_pan_angle(30)
        sleep(0.5)
        self.px.set_cam_pan_angle(0)
        sleep(0.5)
        self.px.set_cam_tilt_angle(-30)
        sleep(0.5)
        self.px.set_cam_tilt_angle(30)
        sleep(0.5)
        self.px.set_cam_tilt_angle(0)
        sleep(0.5)

    def reset_calibration(self) -> Dict[str, str]:
        for servo in [
            self.px.steering_servo,
            self.px.cam_tilt_servo,
            self.px.cam_pan_servo,
        ]:
            servo.reset_calibration()
        self.px.motor_controller.reset_calibration()
        return self.get_calibration_data()

    def increase_servo_angle(self, value: float) -> float:
        return round(constrain(value + self.step, -20, 20), 2)

    def decrease_servo_angle(self, value: float) -> float:
        return round(constrain(value - self.step, -20, 20), 2)

    def increase_servo_dir_angle(self) -> Dict[str, Any]:
        self.px.steering_servo.update_calibration(
            self.increase_servo_angle(self.px.steering_servo.calibration_offset)
        )
        return self.get_calibration_data()

    def decrease_servo_dir_angle(self) -> Dict[str, str]:
        self.px.steering_servo.update_calibration(
            self.decrease_servo_angle(self.px.steering_servo.calibration_offset)
        )
        return self.get_calibration_data()

    def increase_cam_pan_angle(self) -> Dict[str, str]:
        self.px.cam_pan_servo.update_calibration(
            self.increase_servo_angle(self.px.cam_pan_servo.calibration_offset)
        )
        return self.get_calibration_data()

    def decrease_cam_pan_angle(self) -> Dict[str, str]:
        self.px.cam_pan_servo.update_calibration(
            self.decrease_servo_angle(self.px.cam_pan_servo.calibration_offset)
        )
        return self.get_calibration_data()

    def increase_cam_tilt_angle(self) -> Dict[str, str]:
        self.px.cam_tilt_servo.update_calibration(
            self.increase_servo_angle(self.px.cam_tilt_servo.calibration_offset)
        )
        return self.get_calibration_data()

    def decrease_cam_tilt_angle(self) -> Dict[str, str]:
        self.px.cam_tilt_servo.update_calibration(
            self.decrease_servo_angle(self.px.cam_tilt_servo.calibration_offset)
        )
        return self.get_calibration_data()

    def save_calibration(self) -> Dict[str, Any]:
        config = ConfigSchema(**self.config_manager.load_settings())
        steering_servo_offset = self.px.steering_servo.calibration_offset
        cam_pan_servo_offset = self.px.cam_pan_servo.calibration_offset
        cam_tilt_servo_offset = self.px.cam_tilt_servo.calibration_offset
        left_motor = self.px.motor_controller.left_motor.calibration_direction
        right_motor = self.px.motor_controller.right_motor.calibration_direction

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
            "left_motor_direction": self.px.motor_controller.left_motor.calibration_direction,
            "right_motor_direction": self.px.motor_controller.right_motor.calibration_direction,
        }
