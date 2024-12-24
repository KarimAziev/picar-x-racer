from typing import TYPE_CHECKING

from app.schemas.config import ConfigSchema
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from robot_hat import MotorConfig, MotorFabric, MotorService, ServoService

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.services.car_control.config_service import ConfigService


class PicarxAdapter(metaclass=SingletonMeta):
    def __init__(
        self,
        config_manager: "ConfigService",
    ):
        self.config_manager = config_manager

        self.config = ConfigSchema(**config_manager.load_settings())

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

    def set_dir_servo_angle(self, value: float) -> None:
        """
        Set the servo angle for the vehicle's steering direction.

        Args:
           value (int): Desired angle
        """
        self.steering_servo.set_angle(value)

    def set_cam_pan_angle(self, value: int) -> None:
        """
        Set the camera pan angle.

        Args:
           value (int): Desired angle
        """
        self.cam_pan_servo.set_angle(value)

    def set_cam_tilt_angle(self, value: int) -> None:
        """
        Set the camera tilt angle.

        Args:
           value (int): Desired angle
        """
        self.cam_tilt_servo.set_angle(value)

    def move(self, speed: int, direction: int) -> None:
        """
        Move the robot forward or backward.

        Args:
        - speed (int): The base speed at which to move.
        - direction (int): 1 for forward, -1 for backward.
        """
        return self.motor_controller.move(speed, direction)

    def forward(self, speed: int) -> None:
        """
        Move the robot forward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.
        """
        logger.debug("Forward: 100/%s", speed)
        self.move(speed, direction=1)

    def backward(self, speed: int) -> None:
        """
        Move the robot backward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.
        """
        logger.debug("Backward: 100/%s", speed)
        self.move(speed, direction=-1)

    def stop(self) -> None:
        """
        Stop the motors by setting the motor speed pins' pulse width to 0 twice, with a short delay between attempts.
        """
        return self.motor_controller.stop_all()
