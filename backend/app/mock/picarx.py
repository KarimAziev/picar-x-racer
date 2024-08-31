from app.mock.robot_hat_fake_utils import reset_mcu
from app.robot_hat.mock.grayscale_mock import Grayscale_Module
from app.robot_hat.mock.servo_mock import Servo
from app.robot_hat.mock.pwm_mock import PWM
from app.robot_hat.mock.pin_mock import Pin
from app.robot_hat.mock.adc_mock import ADC
from app.robot_hat.filedb import fileDB
from app.config.paths import PICARX_CONFIG_FILE
from app.config.logging_config import setup_logger
import asyncio
import random
import time

logger = setup_logger(__name__)


def constrain(x: int, min_val: int, max_val: int):
    """
    Constrains value to be within a range.
    """
    return max(min_val, min(max_val, x))


class Ultrasonic:
    SOUND_SPEED = 343.3

    def __init__(self, trig, echo, timeout=0.1):
        self.trig = trig
        self.echo = echo
        self.timeout = timeout
        self.dir_current_angle = 0

    async def _read(self):
        await asyncio.sleep(0.001)
        await asyncio.sleep(0.00001)

        return random.choice([random.uniform(0.0, 400.0)])

    async def read(self, times=10):
        for _ in range(times):
            a = await self._read()
            if a != -1:
                return a
        return -1


class Picarx(object):

    ultrasonic: Ultrasonic
    CONFIG = PICARX_CONFIG_FILE

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
        reset_mcu()
        time.sleep(0.2)

        # Set up the config file
        self.config_file = fileDB(config)

        # --------- servos init ---------
        self.cam_pan = Servo(servo_pins[0])

        self.cam_tilt = Servo(servo_pins[1])
        self.dir_servo_pin = Servo(servo_pins[2])
        # Get calibration values
        self.dir_cali_val = float(
            self.config_file.get("picarx_dir_servo", default_value=0) or 0
        )
        self.cam_pan_cali_val = float(
            self.config_file.get("picarx_cam_pan_servo", default_value=0) or 0
        )
        self.cam_tilt_cali_val = float(
            self.config_file.get("picarx_cam_tilt_servo", default_value=0) or 0
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
        self.cali_dir_value = self.config_file.get(
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
        self.line_reference = self.config_file.get(
            "line_reference", default_value=str(self.DEFAULT_LINE_REF)
        )

        self.line_reference = (
            [float(i) for i in self.line_reference.strip("[]").split(",")]
            if self.line_reference
            else self.DEFAULT_LINE_REF
        )
        self.cliff_reference = self.config_file.get(
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
        self.ultrasonic = Ultrasonic(trig, echo)

    def forward(self, speed: int):
        logger.info(f"Moving forward with speed {speed}")

    def backward(self, speed: int):
        logger.info(f"Moving backward with speed {speed}")

    def stop(self):
        for _ in range(2):
            time.sleep(0.002)
        logger.info("Stopped")

    def dir_servo_calibrate(self, value):
        self.dir_cali_val = value
        self.config_file.set("picarx_dir_servo", str(value))
        self.dir_servo_pin.angle(value)

    def set_dir_servo_angle(self, value):
        self.dir_current_angle = constrain(value, self.DIR_MIN, self.DIR_MAX)
        angle_value = self.dir_current_angle + self.dir_cali_val
        self.dir_servo_pin.angle(angle_value)

    def cam_pan_servo_calibrate(self, value):
        self.cam_pan_cali_val = value
        self.config_file.set("picarx_cam_pan_servo", str(value))
        self.cam_pan.angle(value)

    def cam_tilt_servo_calibrate(self, value):
        self.cam_tilt_cali_val = value
        self.config_file.set("picarx_cam_tilt_servo", str(value))
        self.cam_tilt.angle(value)

    def set_cam_pan_angle(self, value):
        value = constrain(value, self.CAM_PAN_MIN, self.CAM_PAN_MAX)
        self.cam_pan.angle(-1 * (value + -1 * self.cam_pan_cali_val))

    def set_cam_tilt_angle(self, value):
        value = constrain(value, self.CAM_TILT_MIN, self.CAM_TILT_MAX)
        self.cam_tilt.angle(-1 * (value + -1 * self.cam_tilt_cali_val))

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
            self.config_file.set("picarx_dir_motor", str(self.cali_dir_value))
        else:
            raise ValueError(
                f"Invalid value {value} for motor calibration. Must be 1 or -1."
            )

    async def get_distance(self):
        return await self.ultrasonic.read()
