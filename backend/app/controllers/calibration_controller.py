from app.util.platform_adapters import Picarx
from time import sleep
from app.util.logger import Logger


class CalibrationController(Logger):
    def __init__(
        self,
        picarx: "Picarx",
        **kwargs,
    ):
        super().__init__(name=__name__, **kwargs)
        self.px = picarx

        self.motor_num = 0
        self.servos_cali = [
            self.px.dir_cali_val,
            self.px.cam_pan_cali_val,
            self.px.cam_tilt_cali_val,
        ]
        self.motors_cali = self.px.cali_dir_value
        self.servos_offset = list.copy(self.servos_cali)
        self.motors_offset = list.copy(self.motors_cali)

        self.motor_run = False

    def servos_test(self):
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

    def servos_move(self, servo_num, value):
        self.logger.info(f"servos_move servo_num {servo_num} value {value}")
        if servo_num == 0:
            self.px.set_dir_servo_angle(value)
        elif servo_num == 1:
            self.px.set_cam_pan_angle(value)
        elif servo_num == 2:
            self.px.set_cam_tilt_angle(value)

    def set_servos_offset(self, servo_num, value):
        if servo_num == 0:
            self.px.dir_cali_val = value
        elif servo_num == 1:
            self.px.cam_pan_cali_val = value
        elif servo_num == 2:
            self.px.cam_tilt_cali_val = value

    def servos_reset(self):
        for i in range(3):
            self.servos_move(i, 0)
        self.get_calibration_data()

    def increase_servo_angle(self, servo_num: int):
        self.servos_offset[servo_num] += 0.4
        if self.servos_offset[servo_num] > 20:
            self.servos_offset[servo_num] = 20

        self.servos_offset[servo_num] = round(self.servos_offset[servo_num], 2)
        self.set_servos_offset(servo_num, self.servos_offset[servo_num])
        self.servos_move(servo_num, servo_num)

    def decrease_servo_angle(self, servo_num: int):
        self.servos_offset[servo_num] -= 0.4
        if self.servos_offset[servo_num] < -20:
            self.servos_offset[servo_num] = -20

        self.servos_offset[servo_num] = round(self.servos_offset[servo_num], 2)
        self.set_servos_offset(servo_num, self.servos_offset[servo_num])
        self.servos_move(servo_num, servo_num)

    def increase_servo_dir_angle(self):
        self.increase_servo_angle(0)
        return self.get_calibration_data()

    def decrease_servo_dir_angle(self):
        self.decrease_servo_angle(0)
        return self.get_calibration_data()

    def increase_cam_pan_angle(self):
        self.increase_servo_angle(1)
        return self.get_calibration_data()

    def decrease_cam_pan_angle(self):
        self.decrease_servo_angle(1)
        return self.get_calibration_data()

    def increase_cam_tilt_angle(self):
        self.increase_servo_angle(2)
        return self.get_calibration_data()

    def decrease_cam_tilt_angle(self):
        self.decrease_servo_angle(2)
        return self.get_calibration_data()

    def save_calibration(self):
        self.px.dir_servo_calibrate(self.servos_offset[0])
        self.px.cam_pan_servo_calibrate(self.servos_offset[1])
        self.px.cam_tilt_servo_calibrate(self.servos_offset[2])
        self.px.motor_direction_calibrate(
            self.motor_num + 1, self.motors_offset[self.motor_num]
        )
        return self.get_calibration_data()

    def get_calibration_data(self):
        return {
            "picarx_dir_servo": f"{self.px.dir_cali_val}",
            "picarx_cam_pan_servo": f"{self.px.cam_pan_cali_val}",
            "picarx_cam_tilt_servo": f"{self.px.cam_tilt_cali_val}",
            "picarx_dir_motor": f"{self.px.cali_dir_value}",
        }
