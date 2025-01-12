from typing import TYPE_CHECKING, Any, Dict

from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.robot import RobotI2CBusError, RobotI2CTimeout
from app.schemas.config import ConfigSchema
from robot_hat import MotorConfig, MotorFabric, MotorService, ServoService

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.managers.json_data_manager import JsonDataManager


class PicarxAdapter(metaclass=SingletonMeta):
    def __init__(
        self,
        config_manager: "JsonDataManager",
    ):
        self.config_manager = config_manager

        self.config = ConfigSchema(**config_manager.load_data())

        self.cam_pan_servo = ServoService(
            servo_pin=self.config.cam_pan_servo.servo_pin,
            calibration_offset=self.config.cam_pan_servo.calibration_offset,
            min_angle=self.config.cam_pan_servo.min_angle,
            max_angle=self.config.cam_pan_servo.max_angle,
            calibration_mode=self.config.cam_pan_servo.calibration_mode,
            name=self.config.cam_pan_servo.name,
        )
        self.cam_tilt_servo = ServoService(
            servo_pin=self.config.cam_tilt_servo.servo_pin,
            calibration_offset=self.config.cam_tilt_servo.calibration_offset,
            min_angle=self.config.cam_tilt_servo.min_angle,
            max_angle=self.config.cam_tilt_servo.max_angle,
            calibration_mode=self.config.cam_tilt_servo.calibration_mode,
            name=self.config.cam_tilt_servo.name,
        )
        self.steering_servo = ServoService(
            servo_pin=self.config.steering_servo.servo_pin,
            calibration_offset=self.config.steering_servo.calibration_offset,
            min_angle=self.config.steering_servo.min_angle,
            max_angle=self.config.steering_servo.max_angle,
            calibration_mode=self.config.steering_servo.calibration_mode,
            name=self.config.steering_servo.name,
        )

        left_motor, right_motor = MotorFabric.create_motor_pair(
            MotorConfig(
                dir_pin=self.config.left_motor.dir_pin,
                pwm_pin=self.config.left_motor.pwm_pin,
                calibration_direction=self.config.left_motor.calibration_direction,
                max_speed=self.config.left_motor.max_speed,
                name=self.config.left_motor.name,
                period=self.config.left_motor.period,
                prescaler=self.config.left_motor.prescaler,
            ),
            MotorConfig(
                dir_pin=self.config.right_motor.dir_pin,
                pwm_pin=self.config.right_motor.pwm_pin,
                calibration_direction=self.config.right_motor.calibration_direction,
                max_speed=self.config.right_motor.max_speed,
                name=self.config.right_motor.name,
                period=self.config.right_motor.period,
                prescaler=self.config.right_motor.prescaler,
            ),
        )

        self.motor_controller = MotorService(
            left_motor=left_motor, right_motor=right_motor
        )

    @property
    def motor_addresses(self) -> list[int]:
        """
        Get the I2C addresses for the left and right motors' speed pins.
        """
        return [
            self.motor_controller.left_motor.speed_pin.address,
            self.motor_controller.right_motor.speed_pin.address,
        ]

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
            "speed": self.motor_controller.speed,
            "direction": self.motor_controller.direction,
            "steering_servo_angle": self.steering_servo.current_angle,
            "cam_pan_angle": self.cam_pan_servo.current_angle,
            "cam_tilt_angle": self.cam_tilt_servo.current_angle,
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
        try:
            self.steering_servo.set_angle(value)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation="set direction servo angle",
                addresses=[self.steering_servo.servo.address],
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation="set direction servo angle",
                addresses=[self.steering_servo.servo.address],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, 'strerror') else str(e),
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
        try:
            self.cam_pan_servo.set_angle(value)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation="set camera pan angle",
                addresses=[self.cam_pan_servo.servo.address],
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation="set camera pan angle",
                addresses=[self.cam_pan_servo.servo.address],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, 'strerror') else str(e),
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
        try:
            self.cam_tilt_servo.set_angle(value)
        except TimeoutError:
            raise RobotI2CTimeout(
                operation="set camera tilt angle",
                addresses=[self.cam_tilt_servo.servo.address],
            )
        except OSError as e:
            raise RobotI2CBusError(
                operation="set camera tilt angle",
                addresses=[self.cam_tilt_servo.servo.address],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, 'strerror') else str(e),
            )

    def move(self, speed: int, direction: int) -> None:
        """
        Move the robot forward or backward.

        Args:
        - speed (int): The base speed at which to move.
        - direction (int): 1 for forward, -1 for backward.
        """
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
                strerror=e.strerror if hasattr(e, 'strerror') else str(e),
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
                addresses=[
                    self.motor_controller.left_motor.speed_pin.address,
                    self.motor_controller.right_motor.speed_pin.address,
                ],
                errno=e.errno,
                strerror=e.strerror if hasattr(e, 'strerror') else str(e),
            )

    def stop(self) -> None:
        """
        Stop the motors by setting the motor speed pins' pulse width to 0 twice, with a short delay between attempts.

        Raises:
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
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
                strerror=e.strerror if hasattr(e, 'strerror') else str(e),
            )
