import asyncio

from app.adapters.robot_hat.adc import ADC
from app.adapters.robot_hat.filedb import fileDB
from app.adapters.robot_hat.grayscale import Grayscale_Module
from app.adapters.robot_hat.pin import Pin
from app.adapters.robot_hat.pwm import PWM
from app.adapters.robot_hat.servo import Servo
from app.adapters.robot_hat.ultrasonic import Ultrasonic
from app.config.paths import PICARX_CONFIG_FILE
from app.util.constrain import constrain
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta


class PicarxAdapter(metaclass=SingletonMeta):
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
        self.logger = Logger(name=__name__)

        # Set up the config file
        self.config_file = fileDB(config)

        # --------- servos init ---------
        self.cam_pan = Servo(servo_pins[0])
        self.cam_tilt = Servo(servo_pins[1])
        self.dir_servo_pin = Servo(servo_pins[2])
        # Get calibration values
        cali_val = self.config_file.get("picarx_dir_servo")
        cali_val_float = float(cali_val) if cali_val else 0.0
        self.dir_cali_val = cali_val_float
        self.logger.debug(f"dir_cali_val {self.dir_cali_val}")

        self.cam_pan_cali_val = float(
            self.config_file.get("picarx_cam_pan_servo", default_value=0) or 0
        )
        self.logger.debug(f"init cam_pan_cali_val with {self.cam_pan_cali_val}")
        self.cam_tilt_cali_val = float(
            self.config_file.get("picarx_cam_tilt_servo", default_value=0) or 0
        )
        self.logger.debug(f"init cam_tilt_cali_val with {self.cam_tilt_cali_val}")
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
        temp: str = (
            self.config_file.get("picarx_dir_motor", default_value="[1, 1]") or "[1, 1]"
        )
        self.cali_dir_value = (
            [int(i.strip()) for i in temp.strip("[]").split(",") if i.strip().isdigit()]
            if temp
            else [1, 1]
        )
        self.logger.debug(f"Initted cali_dir_value with {self.cali_dir_value}")
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
        self.ultrasonic = Ultrasonic(
            Pin(trig), Pin(echo, mode=Pin.IN, pull=Pin.PULL_DOWN)
        )

    def set_motor_speed(self, motor: int, speed: float):
        """
        Set motor speed.

        Args:
           motor (int): Motor index (1 = left motor, 2 = right motor)
           speed (int): Speed value between -100 and 100
        """
        # Map motor indices to names for logging
        motor_names = {1: "left", 2: "right"}
        motor_name = motor_names.get(motor, "unknown")

        speed = max(-100, min(100, speed))

        motor_index = motor - 1

        # Log the action with constrained speed
        self.logger.debug(
            f"Setting speed {speed} for {motor_name} motor (Motor {motor})"
        )

        # Verify calibration values are set and valid
        if not isinstance(self.cali_dir_value, list) or not self.cali_dir_value:
            msg = "Calibration direction values are not set properly."
            self.logger.error(msg)
            raise ValueError(msg)

        if not isinstance(self.cali_speed_value, list) or not self.cali_speed_value:
            msg = "Calibration speed values are not set properly."
            self.logger.error(msg)
            raise ValueError(msg)

        # Validate motor index is within the range of calibration arrays
        if motor_index < 0 or motor_index >= len(self.cali_dir_value):
            msg = f"Motor index {motor} is out of range."
            self.logger.error(msg)
            raise IndexError(msg)

        # Retrieve calibration values for the motor
        calibration_direction = self.cali_dir_value[motor_index]
        calibration_speed_offset = self.cali_speed_value[motor_index]

        # Ensure calibration direction is an integer (1 or -1)
        if calibration_direction not in (-1, 1):
            msg = "Calibration direction should be -1 or 1."
            self.logger.error(msg)
            raise ValueError(msg)

        # Determine actual motor direction based on speed and calibration
        direction = calibration_direction if speed >= 0 else -calibration_direction

        # Compute PWM speed value
        abs_speed = abs(speed)
        if abs_speed != 0:
            pwm_speed = int(abs_speed / 2) + 50
        else:
            pwm_speed = 0

        pwm_speed -= calibration_speed_offset

        pwm_speed = max(0, min(100, pwm_speed))

        # Set motor direction pin
        if direction == -1:
            self.motor_direction_pins[motor_index].high()
        else:
            self.motor_direction_pins[motor_index].low()

        # Set motor speed using Pulse Width Modulation (PWM)
        self.motor_speed_pins[motor_index].pulse_width_percent(pwm_speed)

        # Log the final PWM speed and direction
        self.logger.debug(
            f"Motor {motor_name} (Motor {motor}) set to PWM speed {pwm_speed} with direction {'reverse' if direction == -1 else 'forward'}"
        )

    def motor_speed_calibration(self, value):
        self.cali_speed_value = (
            value if isinstance(value, list) and len(value) == 2 else [0, 0]
        )

    def motor_direction_calibrate(self, motor: int, value: int):
        """
        Set motor direction calibration value.

        Args:
           motor (int): Motor index (1 for left motor, 2 for right motor)
           value (int): Calibration value (1 or -1)
        """
        if motor not in (1, 2):
            raise ValueError("Motor index must be 1 (left) or 2 (right).")

        if value not in (1, -1):
            raise ValueError("Calibration value must be 1 or -1.")

        motor_index = motor - 1  # Adjust for zero-based indexing
        self.cali_dir_value[motor_index] = value
        self.config_file.set("picarx_dir_motor", str(self.cali_dir_value))

    def dir_servo_calibrate(self, value: int):
        """
        Calibrate the steering direction servo.

        Args:
           value (int): Calibration value
        """
        self.dir_cali_val = value
        self.config_file.set("picarx_dir_servo", str(value))
        self.dir_servo_pin.angle(value)

    def set_dir_servo_angle(self, value: int):
        """
        Set the servo angle for the vehicle's steering direction.

        Args:
           value (int): Desired angle
        """
        original_value = self.dir_current_angle
        self.dir_current_angle = constrain(value, self.DIR_MIN, self.DIR_MAX)
        angle_value = self.dir_current_angle + self.dir_cali_val

        self.logger.debug(
            f"Updating direction angle from {original_value} to {self.dir_current_angle} "
            f"(calibrated {angle_value})"
        )
        self.dir_servo_pin.angle(angle_value)

    def cam_pan_servo_calibrate(self, value: int):
        """
        Calibrate the camera pan servo.

        Args:
           value (int): Calibration value
        """
        self.cam_pan_cali_val = value
        self.config_file.set("picarx_cam_pan_servo", str(value))
        self.cam_pan.angle(value)

    def cam_tilt_servo_calibrate(self, value: int):
        """
        Calibrate the camera tilt servo.

        Args:
           value (int): Calibration value
        """
        self.logger.info(f"Calibrating camera tilt servo with value {value}")
        self.cam_tilt_cali_val = value
        self.config_file.set("picarx_cam_tilt_servo", str(value))
        self.cam_tilt.angle(value)

    def set_cam_pan_angle(self, value: int):
        """
        Set the camera pan angle.

        Args:
           value (int): Desired angle
        """
        constrained_value = constrain(value, self.CAM_PAN_MIN, self.CAM_PAN_MAX)
        angle_value = -(constrained_value + self.cam_pan_cali_val)

        self.logger.debug(f"Setting camera pan angle to {angle_value}")
        self.cam_pan.angle(angle_value)

    def set_cam_tilt_angle(self, value: int):
        """
        Set the camera tilt angle.

        Args:
           value (int): Desired angle
        """
        constrained_value = constrain(value, self.CAM_TILT_MIN, self.CAM_TILT_MAX)
        angle_value = -(constrained_value + self.cam_tilt_cali_val)

        self.logger.debug(f"Setting camera tilt angle to {angle_value}")
        self.cam_tilt.angle(angle_value)

    def move(self, speed: int, direction: int):
        """
        Move the robot forward or backward with steering based on the current angle.

        Args:
        - speed (int): The base speed at which to move.
        - direction (int): 1 for forward, -1 for backward.
        """
        current_angle = self.dir_current_angle
        abs_current_angle = min(abs(current_angle), self.DIR_MAX)
        power_scale = (100 - abs_current_angle) / 100.0

        speed1 = speed * direction
        speed2 = -speed * direction

        if current_angle != 0:
            if current_angle > 0:
                speed1 *= power_scale
            else:
                speed2 *= power_scale

        self.logger.debug(
            f"Move with speed {speed}, direction {direction}, angle {current_angle}, "
            f"power_scale {power_scale:.2f}, motor1_speed {speed1}, motor2_speed {speed2}"
        )

        self.set_motor_speed(1, speed1)
        self.set_motor_speed(2, speed2)

    def forward(self, speed: int):
        """
        Move the robot forward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.
        """
        self.move(speed, direction=1)

    def backward(self, speed: int):
        """
        Move the robot backward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.
        """
        self.move(speed, direction=-1)

    async def stop(self):
        """
        Stop the motors by setting the motor speed pins' pulse width to 0 twice, with a short delay between attempts.

        The motor speed control is set to 0% pulse width twice for each motor, with a small delay (2 ms) between the
        two executions. This is done to ensure that even if a brief command or glitch occurred that could have
        prevented the motors from stopping on the first attempt, the second setting enforces that the motors come
        to a full stop.

        Steps followed:
        1. Set both motors' speed to 0% pulse width.
        2. Wait for 2 milliseconds.
        3. Set both motors' speed to 0% pulse width again.
        4. Wait an additional 2 milliseconds for any remaining process to finalize.
        """
        self.logger.info("Stopping motors")
        self.motor_speed_pins[0].pulse_width_percent(0)
        self.motor_speed_pins[1].pulse_width_percent(0)

        await asyncio.sleep(0.002)

        self.motor_speed_pins[0].pulse_width_percent(0)
        self.motor_speed_pins[1].pulse_width_percent(0)

        await asyncio.sleep(0.002)

        self.logger.debug("Motors Stopped")

    async def get_distance(self):
        """
        Attempt to read the distance measurement.

        Returns:
            float: The measured distance in centimeters. Returns -1 if all attempts fail.
        """
        return await self.ultrasonic.read()

    def set_grayscale_reference(self, value):
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError(
                f"Expected a list of 3 elements for line reference, got {value}"
            )
        self.line_reference = value
        self.grayscale.reference(self.line_reference)
        self.config_file.set("line_reference", str(self.line_reference))

    def get_grayscale_data(self):
        return list.copy(self.grayscale.read())

    def get_line_status(self, gm_val_list):
        return self.grayscale.read_status(gm_val_list)

    def set_line_reference(self, value):
        self.set_grayscale_reference(value)

    def get_cliff_status(self, gm_val_list) -> bool:
        """
        Checks the cliff status based on the grayscale module values.

        Args:
           gm_val_list (list[float] or list[int]): List of grayscale module values.

        Returns:
            True if any value in gm_val_list is less than or equal to the corresponding value in cliff_reference,
            False otherwise.
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
            self.config_file.set("cliff_reference", str(self.cliff_reference))
        else:
            raise ValueError("cliff reference must be a 1*3 list")
