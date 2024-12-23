from time import sleep
from typing import TYPE_CHECKING, Dict

from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter


class CalibrationService(metaclass=SingletonMeta):
    def __init__(
        self,
        picarx: "PicarxAdapter",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.logger = Logger(__name__)
        self.px = picarx

        self.motor_num = 0
        self.servos_cali = [
            self.px.dir_cali_val,
            self.px.cam_pan_cali_val,
            self.px.cam_tilt_cali_val,
        ]
        self.motors_cali = [
            self.px.motor_controller.left_motor.calibration_direction,
            self.px.motor_controller.right_motor.calibration_direction,
        ]
        self.servos_offset = list.copy(self.servos_cali)
        self.motors_offset = list.copy(self.motors_cali)
        self.step = 0.1

        self.motor_run = False

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

    def servos_move(self, servo_num: int, value: int) -> None:
        self.logger.info(f"SERVOS_MOVE servo_num {servo_num} value {value}")
        if servo_num == 0:
            self.logger.debug(f"SERVOS_MOVE set_dir_servo_angle {value}")
            self.px.set_dir_servo_angle(value)
        elif servo_num == 1:
            self.logger.debug(f"SERVOS_MOVE set_cam_pan_angle {value}")
            self.px.set_cam_pan_angle(value)
        elif servo_num == 2:
            self.logger.debug(f"SERVOS_MOVE set_cam_tilt_angle {value}")
            self.px.set_cam_tilt_angle(value)

    def set_servos_offset(self, servo_num: int, value: int) -> None:
        self.logger.debug(f"Setting servos offset {servo_num} to {value}")
        if servo_num == 0:
            self.px.dir_cali_val = value
            self.logger.debug(f"px.dir_cali_val {self.px.dir_cali_val}")
        elif servo_num == 1:
            self.px.cam_pan_cali_val = value
            self.logger.debug(f"px.cam_pan_cali_val {self.px.cam_pan_cali_val}")
        elif servo_num == 2:
            self.px.cam_tilt_cali_val = value
            self.logger.debug(f"px.cam_tilt_cali_val {self.px.cam_tilt_cali_val}")

    def servos_reset(self) -> Dict[str, str]:
        for i in range(3):
            self.servos_move(i, 0)
        return self.get_calibration_data()

    def increase_servo_angle(self, servo_num: int) -> None:
        self.servos_offset[servo_num] += self.step
        if self.servos_offset[servo_num] > 20:
            self.servos_offset[servo_num] = 20
        self.servos_offset[servo_num] = round(self.servos_offset[servo_num], 2)
        self.set_servos_offset(servo_num, self.servos_offset[servo_num])
        self.servos_move(servo_num, 0)

    def decrease_servo_angle(self, servo_num: int) -> None:
        self.servos_offset[servo_num] -= self.step
        if self.servos_offset[servo_num] < -20:
            self.servos_offset[servo_num] = -20
        self.servos_offset[servo_num] = round(self.servos_offset[servo_num], 2)
        self.set_servos_offset(servo_num, self.servos_offset[servo_num])
        self.servos_move(servo_num, 0)

    def increase_servo_dir_angle(self) -> Dict[str, str]:
        self.increase_servo_angle(0)
        return self.get_calibration_data()

    def decrease_servo_dir_angle(self) -> Dict[str, str]:
        self.decrease_servo_angle(0)
        return self.get_calibration_data()

    def increase_cam_pan_angle(self) -> Dict[str, str]:
        self.increase_servo_angle(1)
        return self.get_calibration_data()

    def decrease_cam_pan_angle(self) -> Dict[str, str]:
        self.decrease_servo_angle(1)
        return self.get_calibration_data()

    def increase_cam_tilt_angle(self) -> Dict[str, str]:
        self.increase_servo_angle(2)
        return self.get_calibration_data()

    def decrease_cam_tilt_angle(self) -> Dict[str, str]:
        self.decrease_servo_angle(2)
        return self.get_calibration_data()

    def save_calibration(self) -> Dict[str, str]:
        self.px.dir_servo_calibrate(self.servos_offset[0])
        self.px.cam_pan_servo_calibrate(self.servos_offset[1])
        self.px.cam_tilt_servo_calibrate(self.servos_offset[2])
        self.px.motor_direction_calibrate(
            self.motor_num + 1, self.motors_offset[self.motor_num]
        )
        return self.get_calibration_data()

    def get_calibration_data(self) -> Dict[str, str]:
        return {
            "picarx_dir_servo": f"{self.px.dir_cali_val}",
            "picarx_cam_pan_servo": f"{self.px.cam_pan_cali_val}",
            "picarx_cam_tilt_servo": f"{self.px.cam_tilt_cali_val}",
            "picarx_dir_motor": str(
                [
                    self.px.motor_controller.left_motor.calibration_direction,
                    self.px.motor_controller.right_motor.calibration_direction,
                ]
            ),
        }
