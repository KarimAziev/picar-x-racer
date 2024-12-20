import time

from app.util.constrain import constrain
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from robot_hat import PWM, Pin

logger = Logger(__name__)


class MotorAdapter(metaclass=SingletonMeta):
    def __init__(
        self,
        motor_pins: list[str],
        cali_dir_value: list[int] = [1, 1],
        max_speed=100,
        period=4095,
        prescaler=10,
    ):
        """
        Initialize the MotorAdapter.

        Args:
            motor_pins: Motor control pins in order: [left_dir_pin, right_dir_pin, left_pwm_pin, right_pwm_pin].
            cali_dir_value: Initial calibration direction values for each motor.
        """
        # Motor pins
        self.max_speed = max_speed
        self.period = period
        self.prescaler = prescaler
        self.direction_pins = [Pin(motor_pins[0]), Pin(motor_pins[1])]
        self.speed_pins = [PWM(motor_pins[2]), PWM(motor_pins[3])]

        # Motor calibration and adjustments
        self.cali_dir_value = cali_dir_value
        self.cali_speed_value = [0, 0]

        # Init PWM properties
        for pwm_pin in self.speed_pins:
            pwm_pin.period(self.period)
            pwm_pin.prescaler(self.prescaler)

    def set_speed(self, motor: int, speed: float):
        """
        Set the speed for a specific motor.

        Args:
            motor (int): Motor index (1 for left, 2 for right).
            speed (float): Speed between -100 and 100.
        """
        motor_names = {1: "left", 2: "right"}
        motor_name = motor_names.get(motor, "unknown")

        speed = constrain(speed, -self.max_speed, self.max_speed)

        motor_index = motor - 1

        # Log the action with constrained speed
        logger.debug(
            "Setting speed %s for %s motor (Motor %s)", speed, motor_name, motor
        )

        # Verify calibration values are set and valid
        if not isinstance(self.cali_dir_value, list) or not self.cali_dir_value:
            msg = "Calibration direction values are not set properly."
            logger.error(msg)
            raise ValueError(msg)

        if not isinstance(self.cali_speed_value, list) or not self.cali_speed_value:
            msg = "Calibration speed values are not set properly."
            logger.error(msg)
            raise ValueError(msg)

        # Validate motor index is within the range of calibration arrays
        if motor_index < 0 or motor_index >= len(self.cali_dir_value):
            msg = f"Motor index {motor} is out of range."
            logger.error(msg)
            raise IndexError(msg)

        # Retrieve calibration values for the motor
        calibration_direction = self.cali_dir_value[motor_index]
        calibration_speed_offset = self.cali_speed_value[motor_index]

        # Ensure calibration direction is an integer (1 or -1)
        if calibration_direction not in (-1, 1):
            msg = "Calibration direction should be -1 or 1."
            logger.error(msg)
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

        pwm_speed = constrain(pwm_speed, 0, 100)

        # Set motor direction pin
        if direction == -1:
            self.direction_pins[motor_index].high()
        else:
            self.direction_pins[motor_index].low()

        # Set motor speed using Pulse Width Modulation (PWM)
        self.speed_pins[motor_index].pulse_width_percent(pwm_speed)

        logger.debug(
            "%s motor set PWM speed %s and %s direction",
            motor_name,
            pwm_speed,
            'reverse' if direction == -1 else 'forward',
        )

    def calibrate_speed(self, cali_values: list[int]):
        """
        Set motor speed calibration values.
        """
        if len(cali_values) == len(self.cali_speed_value):
            self.cali_speed_value = cali_values
        else:
            raise ValueError("Invalid motor length!")

    def calibrate_direction(self, motor: int, cali_value: int):
        """
        Set motor direction calibration value.

        Args:
           motor (int): Motor index (1 for left motor, 2 for right motor)
           value (int): Calibration value (1 or -1)
        """
        if motor not in (1, 2):
            raise ValueError("Motor index must be 1 (left) or 2 (right).")

        if cali_value not in (1, -1):
            raise ValueError("Calibration value must be 1 or -1.")

        self.cali_dir_value[motor - 1] = cali_value

    def stop(self) -> None:
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
        logger.debug("Stopping motors")
        self.speed_pins[0].pulse_width_percent(0)
        self.speed_pins[1].pulse_width_percent(0)

        time.sleep(0.002)

        self.speed_pins[0].pulse_width_percent(0)
        self.speed_pins[1].pulse_width_percent(0)

        time.sleep(0.002)

        logger.debug("Motors Stopped")
