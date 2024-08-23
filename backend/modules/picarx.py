from robot_hat import Pin, ADC, PWM, Servo, fileDB
from .ultrasonic import Ultrasonic
from robot_hat import Grayscale_Module, utils
import time
import os


def constrain(x, min_val: int, max_val: int):
    """
    Constrains value to be within a range.
    """
    return max(min_val, min(max_val, x))


class Picarx:
    CONFIG = "/opt/picar-x/picar-x.conf"

    DEFAULT_LINE_REF = [1000, 1000, 1000]
    DEFAULT_CLIFF_REF = [500, 500, 500]

    DIR_MIN = -30
    DIR_MAX = 30
    CAM_PAN_MIN = -90
    CAM_PAN_MAX = 90
    CAM_TILT_MIN = -35
    CAM_TILT_MAX = 65

    PERIOD = 4095
    PRESCALER = 10
    TIMEOUT = 0.02

    def __init__(
        self,
        servo_pins: list[str] = ["P0", "P1", "P2"],
        motor_pins: list[str] = ["D4", "D5", "P12", "P13"],
        grayscale_pins: list[str] = ["A0", "A1", "A2"],
        ultrasonic_pins: list[str] = ["D2", "D3"],
        config: str = CONFIG,
    ):
        # reset robot_hat
        utils.reset_mcu()
        time.sleep(0.2)

        # Set up the config file
        self.config_flie = fileDB(config, "777", os.getlogin())

        # --------- servos init ---------
        self.cam_pan = Servo(servo_pins[0])
        self.cam_tilt = Servo(servo_pins[1])
        self.dir_servo_pin = Servo(servo_pins[2])
        # Get calibration values
        self.dir_cali_val = float(
            self.config_flie.get("picarx_dir_servo", default_value=0) or 0
        )
        self.cam_pan_cali_val = float(
            self.config_flie.get("picarx_cam_pan_servo", default_value=0) or 0
        )
        self.cam_tilt_cali_val = float(
            self.config_flie.get("picarx_cam_tilt_servo", default_value=0) or 0
        )
        # Set servos to init angle
        self.dir_servo_pin.angle(self.dir_cali_val)
        self.cam_pan.angle(self.cam_pan_cali_val)
        self.cam_tilt.angle(self.cam_tilt_cali_val)

        # --------- motors init ---------
        self.left_rear_dir_pin = Pin(motor_pins[0])
        self.right_rear_dir_pin = Pin(motor_pins[1])
        self.left_rear_pwm_pin = PWM(motor_pins[2])
        self.right_rear_pwm_pin = PWM(motor_pins[3])
        self.motor_direction_pins = [self.left_rear_dir_pin, self.right_rear_dir_pin]
        self.motor_speed_pins = [self.left_rear_pwm_pin, self.right_rear_pwm_pin]
        # Get calibration values
        self.cali_dir_value = self.config_flie.get(
            "picarx_dir_motor", default_value="[1, 1]"
        )
        self.cali_dir_value = (
            [
                int(i.strip())
                for i in self.cali_dir_value.strip("[]").split(",")
                if i.strip().isdigit()
            ]
            if self.cali_dir_value
            else [1, 1]
        )
        self.cali_speed_value = [0, 0]
        self.dir_current_angle = 0
        # Init pwm
        for pin in self.motor_speed_pins:
            pin.period(self.PERIOD)
            pin.prescaler(self.PRESCALER)

        # --------- grayscale module init ---------
        adc0, adc1, adc2 = [ADC(pin) for pin in grayscale_pins]
        self.grayscale = Grayscale_Module(adc0, adc1, adc2)
        # Get reference
        self.line_reference = self.config_flie.get(
            "line_reference", default_value=str(self.DEFAULT_LINE_REF)
        )
        self.line_reference = (
            [float(i) for i in self.line_reference.strip("[]").split(",")]
            if self.line_reference
            else self.DEFAULT_LINE_REF
        )
        self.cliff_reference = self.config_flie.get(
            "cliff_reference", default_value=str(self.DEFAULT_CLIFF_REF)
        )
        self.cliff_reference = (
            [float(i) for i in self.cliff_reference.strip("[]").split(",")]
            if self.cliff_reference
            else self.DEFAULT_CLIFF_REF
        )
        # Transfer reference
        self.grayscale.reference(self.line_reference)

        # --------- ultrasonic init ---------
        trig, echo = ultrasonic_pins
        self.ultrasonic = Ultrasonic(
            Pin(trig), Pin(echo, mode=Pin.IN, pull=Pin.PULL_DOWN)
        )

    def set_motor_speed(self, motor: int, speed: int):
        """Set motor speed

        param motor: motor index, 1 means left motor, 2 means right motor
        type motor: int
        param speed: speed
        type speed: int
        """
        speed = constrain(speed, -100, 100)
        motor -= 1

        if self.cali_dir_value is None or not self.cali_dir_value:
            raise ValueError("Calibration direction values are not set properly.")
        if self.cali_speed_value is None or not self.cali_speed_value:
            raise ValueError("Calibration speed values are not set properly.")

        if (
            motor < 0
            or motor >= len(self.cali_dir_value)
            or motor >= len(self.cali_speed_value)
        ):
            raise IndexError("Motor index out of range.")
        direction = (
            1 * self.cali_dir_value[motor]
            if speed >= 0
            else -1 * self.cali_dir_value[motor]
        )
        if not isinstance(direction, int):
            raise TypeError("Direction should be an int type.")

        speed = abs(speed)
        if speed != 0:
            speed = int(speed / 2) + 50
        speed -= self.cali_speed_value[motor]

        if direction < 0:
            self.motor_direction_pins[motor].high()
            self.motor_speed_pins[motor].pulse_width_percent(speed)
        else:
            self.motor_direction_pins[motor].low()
            self.motor_speed_pins[motor].pulse_width_percent(speed)

    def motor_speed_calibration(self, value):
        self.cali_speed_value = (
            value if isinstance(value, list) and len(value) == 2 else [0, 0]
        )

    def motor_direction_calibrate(self, motor: int, value: int):
        """Set motor direction calibration value

        param motor: motor index, 1 means left motor, 2 means right motor
        type motor: int
        param value: speed
        type value: int
        """
        motor -= 1  # Adjust for zero-indexing

        if not isinstance(self.cali_dir_value, list) or len(self.cali_dir_value) != 2:
            self.cali_dir_value = [1, 1]

        if value in {1, -1} and 0 <= motor < len(self.cali_dir_value):
            self.cali_dir_value[motor] = value
            self.config_flie.set("picarx_dir_motor", str(self.cali_dir_value))
        else:
            raise ValueError(
                f"Invalid value {value} for motor calibration. Must be 1 or -1."
            )

    def dir_servo_calibrate(self, value):
        self.dir_cali_val = value
        self.config_flie.set("picarx_dir_servo", str(value))
        self.dir_servo_pin.angle(value)

    def set_dir_servo_angle(self, value):
        self.dir_current_angle = constrain(value, self.DIR_MIN, self.DIR_MAX)
        angle_value = self.dir_current_angle + self.dir_cali_val
        self.dir_servo_pin.angle(angle_value)

    def cam_pan_servo_calibrate(self, value):
        self.cam_pan_cali_val = value
        self.config_flie.set("picarx_cam_pan_servo", str(value))
        self.cam_pan.angle(value)

    def cam_tilt_servo_calibrate(self, value):
        self.cam_tilt_cali_val = value
        self.config_flie.set("picarx_cam_tilt_servo", str(value))
        self.cam_tilt.angle(value)

    def set_cam_pan_angle(self, value):
        value = constrain(value, self.CAM_PAN_MIN, self.CAM_PAN_MAX)
        self.cam_pan.angle(-1 * (value + -1 * self.cam_pan_cali_val))

    def set_cam_tilt_angle(self, value):
        value = constrain(value, self.CAM_TILT_MIN, self.CAM_TILT_MAX)
        self.cam_tilt.angle(-1 * (value + -1 * self.cam_tilt_cali_val))

    def set_power(self, speed):
        self.set_motor_speed(1, speed)
        self.set_motor_speed(2, speed)

    def backward(self, speed):
        current_angle = self.dir_current_angle
        abs_current_angle = abs(current_angle)
        if abs_current_angle > self.DIR_MAX:
            abs_current_angle = self.DIR_MAX
        power_scale = (100 - abs_current_angle) / 100.0
        if current_angle != 0:
            if (current_angle / abs_current_angle) > 0:
                self.set_motor_speed(1, -1 * speed)
                self.set_motor_speed(2, speed * power_scale)
            else:
                self.set_motor_speed(1, -1 * speed * power_scale)
                self.set_motor_speed(2, speed)
        else:
            self.set_motor_speed(1, -1 * speed)
            self.set_motor_speed(2, speed)

    def forward(self, speed):
        current_angle = self.dir_current_angle
        abs_current_angle = abs(current_angle)
        if abs_current_angle > self.DIR_MAX:
            abs_current_angle = self.DIR_MAX
        power_scale = (100 - abs_current_angle) / 100.0
        if current_angle != 0:
            if (current_angle / abs_current_angle) > 0:
                self.set_motor_speed(1, speed * power_scale)
                self.set_motor_speed(2, -speed)
            else:
                self.set_motor_speed(1, speed)
                self.set_motor_speed(2, -1 * speed * power_scale)
        else:
            self.set_motor_speed(1, speed)
            self.set_motor_speed(2, -1 * speed)

    def stop(self):
        """
        Execute twice to make sure it stops
        """
        for _ in range(2):
            self.motor_speed_pins[0].pulse_width_percent(0)
            self.motor_speed_pins[1].pulse_width_percent(0)
            time.sleep(0.002)

    # def backward(self, speed):
    #     current_angle = self.dir_current_angle
    #     if current_angle != 0:
    #         abs_current_angle = abs(current_angle)
    #         if abs_current_angle > self.DIR_MAX:
    #             abs_current_angle = self.DIR_MAX
    #         power_scale = (100 - abs_current_angle) / 100.0
    #         if (current_angle / abs_current_angle) > 0:
    #             self.set_motor_speed(1, -1*speed)
    #             self.set_motor_speed(2, speed * power_scale)
    #         else:
    #             self.set_motor_speed(1, -1*speed * power_scale)
    #             self.set_motor_speed(2, speed )
    #     else:
    #         self.set_motor_speed(1, -1*speed)
    #         self.set_motor_speed(2, speed)

    # def forward(self, speed):
    #     current_angle = self.dir_current_angle
    #     if current_angle != 0:
    #         abs_current_angle = abs(current_angle)
    #         if abs_current_angle > self.DIR_MAX:
    #             abs_current_angle = self.DIR_MAX
    #         power_scale = (100 - abs_current_angle) / 100.0
    #         if (current_angle / abs_current_angle) > 0:
    #             self.set_motor_speed(1, 1*speed * power_scale)
    #             self.set_motor_speed(2, -speed)
    #         else:
    #             self.set_motor_speed(1, speed)
    #             self.set_motor_speed(2, -1*speed * power_scale)
    #     else:
    #         self.set_motor_speed(1, speed)
    #         self.set_motor_speed(2, -1*speed)

    def get_distance(self):
        return self.ultrasonic.read()

    def set_grayscale_reference(self, value):
        if isinstance(value, list) and len(value) == 3:
            self.line_reference = value
            self.grayscale.reference(self.line_reference)
            self.config_flie.set("line_reference", str(self.line_reference))
        else:
            raise ValueError("grayscale reference must be a 1*3 list")

    def get_grayscale_data(self):
        return list.copy(self.grayscale.read())

    def get_line_status(self, gm_val_list):
        return self.grayscale.read_status(gm_val_list)

    def set_line_reference(self, value):
        self.set_grayscale_reference(value)

    def get_cliff_status(self, gm_val_list):
        """
        Checks the cliff status based on the grayscale module values.

        :param gm_val_list: List of grayscale module values.
        :type gm_val_list: list[float] or list[int]
        :return: True if any value in gm_val_list is less than or equal to the corresponding value in cliff_reference, False otherwise.
        :rtype: bool
        """
        if gm_val_list is not None and self.cliff_reference is not None:
            if len(gm_val_list) == 3 and len(self.cliff_reference) == 3:
                for i in range(3):
                    if gm_val_list[i] <= self.cliff_reference[i]:
                        return True
        return False

    def set_cliff_reference(self, value):
        if isinstance(value, list) and len(value) == 3:
            self.cliff_reference = value
            self.config_flie.set("cliff_reference", str(self.cliff_reference))
        else:
            raise ValueError("cliff reference must be a 1*3 list")


if __name__ == "__main__":
    px = Picarx()
    px.forward(50)
    time.sleep(1)
    px.stop()