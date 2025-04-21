from typing import TYPE_CHECKING, Any, Dict, List, Type, Union

from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.robot import RobotI2CBusError, RobotI2CTimeout
from app.schemas.config import (
    AngularServoConfig,
    DCMotorConfig,
    GPIOAngularServoConfig,
    HardwareConfig,
    HBridgeMotorConfig,
)
from robot_hat import MotorService, Pin, ServoService, SMBus
from robot_hat.drivers.pwm.pca9685 import PCA9685
from robot_hat.drivers.pwm.sunfounder_pwm import SunfounderPWM
from robot_hat.motor.dc_motor import DCMotor
from robot_hat.motor.motor import HBridgeMotor
from robot_hat.motor.motor_abc import MotorABC
from robot_hat.servos.gpio_angular_servo import GPIOAngularServo
from robot_hat.servos.servo import Servo

logger = Logger(name=__name__, app_name="px_robot")

if TYPE_CHECKING:
    from app.managers.file_management.json_data_manager import JsonDataManager


class PicarxAdapter(metaclass=SingletonMeta):
    pwm_drivers: Dict[str, Union[Type[PCA9685], Type[SunfounderPWM]]] = {
        "PCA9685": PCA9685,
        "Sunfounder": SunfounderPWM,
    }

    def __init__(
        self,
        config_manager: "JsonDataManager",
    ):
        self.config_manager = config_manager

        self.config = HardwareConfig(**config_manager.load_data())

        self.smbus = SMBus(1)

        self.cam_pan_servo = (
            self._make_servo(self.config.cam_pan_servo)
            if self.config.cam_pan_servo
            else None
        )
        self.cam_tilt_servo = (
            self._make_servo(self.config.cam_tilt_servo)
            if self.config.cam_tilt_servo
            else None
        )
        self.steering_servo = (
            self._make_servo(self.config.steering_servo)
            if self.config.steering_servo
            else None
        )

        self.left_motor = (
            self._make_motor(self.config.left_motor) if self.config.left_motor else None
        )

        self.right_motor = (
            self._make_motor(self.config.right_motor)
            if self.config.right_motor
            else None
        )

        self.motor_controller = (
            MotorService(left_motor=self.left_motor, right_motor=self.right_motor)
            if self.left_motor and self.right_motor
            else None
        )

    def _make_motor(
        self, motor_config: Union[HBridgeMotorConfig, DCMotorConfig]
    ) -> MotorABC:
        if isinstance(motor_config, DCMotorConfig):
            return DCMotor(
                forward_pin=motor_config.forward_pin,
                backward_pin=motor_config.backward_pin,
                pwm_pin=motor_config.enable_pin,
                calibration_direction=motor_config.calibration_direction,
                max_speed=motor_config.max_speed,
                name=motor_config.name,
                pwm=motor_config.pwm,
            )
        else:
            driver_cls = self.pwm_drivers[motor_config.driver.name]

            driver = driver_cls(
                bus=self.smbus,
                address=motor_config.driver.addr_int,
                frame_width=motor_config.driver.frame_width or 20000,
            )
            return HBridgeMotor(
                channel=motor_config.channel,
                driver=driver,
                frequency=motor_config.driver.freq,
                dir_pin=Pin(motor_config.dir_pin),
                calibration_direction=motor_config.calibration_direction,
                max_speed=motor_config.max_speed,
            )

    def _make_servo(
        self, servo_config: Union[GPIOAngularServoConfig, AngularServoConfig]
    ) -> ServoService:
        if isinstance(servo_config, AngularServoConfig):
            driver_cls = self.pwm_drivers[servo_config.driver.name]

            driver = driver_cls(
                bus=self.smbus,
                address=servo_config.driver.addr_int,
                frame_width=servo_config.driver.frame_width or 20000,
            )

            servo = Servo(
                channel=servo_config.channel,
                driver=driver,
                min_angle=servo_config.min_angle,
                max_angle=servo_config.max_angle,
                min_pulse=servo_config.min_pulse,
                max_pulse=servo_config.max_pulse,
            )
            if servo_config.driver.freq:
                driver.set_pwm_freq(servo_config.driver.freq)
        else:
            servo = GPIOAngularServo(
                servo_config.pin,
                min_angle=servo_config.min_angle,
                max_angle=servo_config.max_angle,
                min_pulse=servo_config.min_pulse,
                max_pulse=servo_config.max_pulse,
            )
        return ServoService(
            servo=servo,
            calibration_offset=servo_config.calibration_offset,
            min_angle=servo_config.min_angle,
            max_angle=servo_config.max_angle,
            calibration_mode=servo_config.calibration_mode,
            name=servo_config.name,
        )

    @property
    def motor_addresses(self) -> List[int]:
        """
        Get the I2C addresses for the left and right motors' speed pins.
        """
        return []

    @property
    def state(self) -> Dict[str, Any]:
        """
        Returns key metrics of the current state as a dictionary.

        The returned dictionary contains:
        - "speed": Current speed.
        - "direction": Current travel direction.
        - "steering_servo_angle": Current servo direction angle.
        - "cam_pan_angle": Current camera pan angle.
        - "cam_tilt_angle": Current camera tilt angle.
        """
        return {
            "speed": self.motor_controller.speed if self.motor_controller else 0,
            "direction": (
                self.motor_controller.direction if self.motor_controller else 0
            ),
            "steering_servo_angle": (
                self.steering_servo.current_angle if self.steering_servo else 0
            ),
            "cam_pan_angle": (
                self.cam_pan_servo.current_angle if self.cam_pan_servo else 0
            ),
            "cam_tilt_angle": (
                self.cam_tilt_servo.current_angle if self.cam_tilt_servo else 0
            ),
        }

    def set_dir_servo_angle(self, value: float) -> None:
        """
        Set the servo angle for the vehicle's steering direction.

        Args:
           value (float): Desired angle

        Raises:
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        if not self.steering_servo:
            raise ValueError("Direction servo is not configured")
        try:
            self.steering_servo.set_angle(value)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation="set direction servo angle",
                addresses=[],
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation="set direction servo angle",
                addresses=[],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, "strerror") else str(e),
            )

    def set_cam_pan_angle(self, value: int) -> None:
        """
        Set the camera pan angle.

        Args:
           value (int): Desired angle

        Raises:
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        if not self.cam_pan_servo:
            raise ValueError("Camera pan servo is not configured")
        try:
            self.cam_pan_servo.set_angle(value)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation="set camera pan angle",
                addresses=[],
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation="set camera pan angle",
                addresses=[],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, "strerror") else str(e),
            )

    def set_cam_tilt_angle(self, value: int) -> None:
        """
        Set the camera tilt angle.

        Args:
           value (int): Desired angle

        Raises:
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        if not self.cam_tilt_servo:
            raise ValueError("Camera tilt servo is not configured")

        try:
            self.cam_tilt_servo.set_angle(value)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation="set camera tilt angle",
                addresses=[],
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation="set camera tilt angle",
                addresses=[],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, "strerror") else str(e),
            )

    def move(self, speed: int, direction: int) -> None:
        """
        Move the robot forward or backward.

        Args:
        - speed (int): The base speed at which to move.
        - direction (int): 1 for forward, -1 for backward.
        """
        if not self.motor_controller:
            raise ValueError("Motor controller is not configured")
        self.motor_controller.move(speed, direction)

    def forward(self, speed: int) -> None:
        """
        Move the robot forward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.

        Raises:
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        logger.debug("Forward: 100/%s", speed)
        try:
            self.move(speed, direction=1)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation=f"move forward ({speed})",
                addresses=self.motor_addresses,
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation=f"move forward ({speed})",
                addresses=self.motor_addresses,
                errno=e.errno,
                strerror=e.strerror if hasattr(e, "strerror") else str(e),
            )

    def backward(self, speed: int) -> None:
        """
        Move the robot backward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.

        Raises:
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        logger.debug("Backward: 100/%s", speed)
        try:
            self.move(speed, direction=-1)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation=f"move backward ({speed})",
                addresses=self.motor_addresses,
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation=f"move backward ({speed})",
                addresses=[],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, "strerror") else str(e),
            )

    def stop(self) -> None:
        """
        Stop the motors by setting the motor speed pins' pulse width to 0 twice, with a short delay between attempts.

        Raises:
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        if not self.motor_controller:
            raise ValueError("Motor controller is not configured")
        try:
            return self.motor_controller.stop_all()
        except TimeoutError:
            raise RobotI2CTimeout(
                operation="stop motors",
                addresses=self.motor_addresses,
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation="stop motors",
                addresses=self.motor_addresses,
                errno=e.errno,
                strerror=e.strerror if hasattr(e, "strerror") else str(e),
            )

    def cleanup(self):
        """
        Clean up hardware resources by stopping all motors and gracefully closing all
        associated I2C connections for both motors and servos.
        """

        self.stop()
        try:
            self.smbus.close()
        except Exception as err:
            logger.error("Error closing smbus: %s", err)
