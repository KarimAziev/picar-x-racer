from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from app.core.px_logger import Logger
from app.exceptions.robot import (
    MotorNotFoundError,
    RobotI2CBusError,
    RobotI2CTimeout,
    ServoNotFoundError,
)
from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.motors import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    PhaseMotorConfig,
)
from app.schemas.robot.pwm import PWMDriverConfig
from app.schemas.robot.servos import AngularServoConfig, GPIOAngularServoConfig
from app.types.car import PicarState
from robot_hat import (
    GPIOAngularServo,
    MotorABC,
    MotorFactory,
    MotorService,
    MotorServiceDirection,
    PWMFactory,
    PWMDriverABC,
    Servo,
    ServoService,
    SingleMotorService,
    SMBusManager,
)
from robot_hat.services.base_motor_service import BaseMotorService

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.managers.file_management.json_data_manager import JsonDataManager


class PicarxAdapter:
    def __init__(
        self, config_manager: "JsonDataManager", smbus_manager: SMBusManager
    ) -> None:
        self.config_manager = config_manager
        self.smbus_manager = smbus_manager
        self._motor_addresses: List[int] = []
        self._pwm_drivers: Dict[Tuple[int, int], PWMDriverABC] = {}
        self._pwm_driver_configs: Dict[Tuple[int, int], PWMDriverConfig] = {}
        self.cam_pan_servo: Optional[ServoService] = None
        self.cam_tilt_servo: Optional[ServoService] = None
        self.steering_servo: Optional[ServoService] = None
        self.motors: List[MotorABC] = []
        self.motor_controller: Optional[BaseMotorService] = None
        self.init_hardware()

    def init_hardware(
        self,
        config: Optional[HardwareConfig] = None,
        strict: bool = False,
    ) -> None:
        self.config = (
            config.model_copy(deep=True)
            if config is not None
            else HardwareConfig(**self.config_manager.load_data())
        )

        logger.debug("Initializing config %s", self.config)

        for fn in [
            self._init_pan_servo,
            self._init_tilt_servo,
            self._init_steering_servo,
            self._init_motors,
            self._init_motor_controller,
        ]:
            fn(strict=strict)

    @property
    def motor_addresses(self) -> List[int]:
        """
        Get the I2C addresses for the left and right motors' speed pins.
        """
        return self._motor_addresses

    @property
    def state(self) -> PicarState:
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
        Set the steering servo angle.

        Args:
            value: Desired angle.
        Raises:
            ServoNotFoundError: If servo not configured.
            RobotI2CTimeout: If the operation times out.
            RobotI2CBusError: If the operation fails due to a bus error.
        """
        if not self.steering_servo:
            raise ServoNotFoundError("Steering servo not configured")
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

    def set_cam_pan_angle(self, value: float) -> None:
        """
        Set the camera pan angle.

        Args:
           value: Desired angle

        Raises:
           ServoNotFoundError: If servo not configured.
           RobotI2CTimeout: If the operation times out.
           RobotI2CBusError: If the operation fails due to a bus error.
        """
        if not self.cam_pan_servo:
            raise ServoNotFoundError("Pan servo is not configured")
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

    def set_cam_tilt_angle(self, value: float) -> None:
        """
        Set the camera tilt angle.

        Args:
           value: Desired angle

        Raises:
           ServoNotFoundError: If servo not configured.
           RobotI2CTimeout: If the operation times out.
           RobotI2CBusError: If the operation fails due to a bus error.
        """
        if not self.cam_tilt_servo:
            raise ServoNotFoundError("Tilt servo is not configured")

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

    def move(self, speed: int, direction: MotorServiceDirection) -> None:
        """
        Move the robot forward or backward.

        Args:
        - speed: The base speed at which to move.
        - direction: 1 for forward, -1 for backward.
        """
        if not self.motor_controller:
            raise MotorNotFoundError("Motors not found or not configured")
        self.motor_controller.move(speed, direction)

    def forward(self, speed: int) -> None:
        """
        Move the robot forward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.

        Raises:
           MotorNotFoundError: If the motor controller is not configured or not found.
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        logger.debug("Forward: 100/%s", speed)
        if not self.motor_controller:
            raise MotorNotFoundError("Motors not found or not configured")
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
           MotorNotFoundError: If the motor controller is not configured or not found.
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        logger.debug("Backward: 100/%s", speed)
        if not self.motor_controller:
            raise MotorNotFoundError("Motors not found or not configured")
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
        Stop the motors by setting the motor speed pins' pulse width to 0 twice, with a
        short delay between attempts.

        Raises:
           MotorNotFoundError: If the motor controller is not configured or not found.
           RobotI2CTimeout: If the operation fails due to a timeout.
           RobotI2CBusError: If the operation fails due to a bus-related error.
        """
        if not self.motor_controller:
            raise MotorNotFoundError("Motors not found or not configured")
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

    def cleanup(self) -> None:
        """
        Clean up hardware resources by stopping all motors and gracefully closing all
        associated I2C connections for motors and servos.
        """

        if self.motor_controller:
            try:
                self.stop()
                self.motor_controller.close()
            except RobotI2CTimeout as e:
                logger.error("I2C timeout error closing motors %s", e)
            except RobotI2CBusError as e:
                logger.error("I2C bus error closing motors %s", e)
            except Exception as e:
                logger.error(
                    "Unexpected error while closing motor controller %s",
                    e,
                    exc_info=True,
                )
        else:
            for motor in self.motors:
                if motor:
                    try:
                        motor.close()
                    except Exception as e:
                        logger.error("Error closing motor %s", e)

        self._motor_addresses = []
        self.motors = []
        self.motor_controller = None

        for servo_service in [
            self.steering_servo,
            self.cam_tilt_servo,
            self.cam_pan_servo,
        ]:
            if servo_service:
                try:
                    servo_service.close()
                except (TimeoutError, OSError) as e:
                    err_msg = str(e)
                    logger.error(err_msg)
                except Exception as e:
                    logger.error("Error closing servo %s", e)

        self.steering_servo = None
        self.cam_tilt_servo = None
        self.cam_pan_servo = None

        for driver in self._pwm_drivers.values():
            try:
                driver.close()
            except Exception as e:
                logger.error("Error closing shared PWM driver %s", e)
        self._pwm_drivers.clear()
        self._pwm_driver_configs.clear()

    def _init_pan_servo(self, strict: bool = False) -> None:
        try:
            self.cam_pan_servo = (
                self._make_servo(self.config.cam_pan_servo)
                if self.config.cam_pan_servo and self.config.cam_pan_servo.enabled
                else None
            )
        except (TimeoutError, OSError) as e:
            logger.error("Failed to initialize pan servo: %s", e)
            if strict:
                raise
        except Exception:
            logger.error("Unexpected error while initializing pan servo", exc_info=True)
            if strict:
                raise

    def _init_tilt_servo(self, strict: bool = False) -> None:
        try:
            self.cam_tilt_servo = (
                self._make_servo(self.config.cam_tilt_servo)
                if self.config.cam_tilt_servo and self.config.cam_tilt_servo.enabled
                else None
            )
        except (TimeoutError, OSError) as e:
            logger.error("Failed to initialize tilt servo: %s", e)
            if strict:
                raise
        except Exception:
            logger.error(
                "Unexpected error while initializing tilt servo", exc_info=True
            )
            if strict:
                raise

    def _init_steering_servo(self, strict: bool = False) -> None:
        try:
            self.steering_servo = (
                self._make_servo(self.config.steering_servo)
                if self.config.steering_servo and self.config.steering_servo.enabled
                else None
            )

        except (TimeoutError, OSError) as e:
            logger.error("Failed to initialize steering servo: %s", e)
            if strict:
                raise
        except Exception:
            logger.error(
                "Unexpected error while initializing steering servo", exc_info=True
            )
            if strict:
                raise

    def _init_motor_controller(self, strict: bool = False) -> None:
        try:
            configured_count = len(self.config.motors)
            if configured_count == 1 and len(self.motors) == 1:
                self.motor_controller = SingleMotorService(motor=self.motors[0])
            elif configured_count == 2 and len(self.motors) == 2:
                self.motor_controller = MotorService(
                    left_motor=self.motors[0], right_motor=self.motors[1]
                )
            else:
                self.motor_controller = None

        except (TimeoutError, OSError) as e:
            logger.error("Failed to initialize motors controller: %s", e)
            if strict:
                raise
        except Exception:
            logger.error(
                "Unexpected error initializing motors controller", exc_info=True
            )
            if strict:
                raise

    def _init_motors(self, strict: bool = False) -> None:
        self.motors = []
        for index, motor_config in enumerate(self.config.motors):
            if not motor_config.enabled:
                continue
            try:
                motor = self._make_motor(motor_config)
                if motor:
                    self.motors.append(motor)
                    if isinstance(motor_config, I2CDCMotorConfig):
                        self._motor_addresses.append(motor_config.driver.addr_int)
            except (TimeoutError, OSError) as e:
                logger.error("Failed to initialize motor %s: %s", index + 1, e)
                if strict:
                    raise
            except Exception:
                logger.error(
                    "Unexpected error while initializing motor %s",
                    index + 1,
                    exc_info=True,
                )
                if strict:
                    raise

    def _make_motor(
        self, motor_config: Union[I2CDCMotorConfig, GPIODCMotorConfig, PhaseMotorConfig]
    ) -> Optional[MotorABC]:
        data_class = motor_config.to_dataclass()
        if isinstance(motor_config, I2CDCMotorConfig):
            return MotorFactory.create_motor(
                data_class,
                driver=self._get_pwm_driver(motor_config.driver),
            )
        return MotorFactory.create_motor(data_class)

    def _get_pwm_driver(self, config: PWMDriverConfig) -> PWMDriverABC:
        key = (config.bus, config.addr_int)
        existing = self._pwm_drivers.get(key)
        if existing is not None:
            if (
                self._pwm_driver_configs[key].hardware_signature
                != config.hardware_signature
            ):
                raise ValueError(
                    "Conflicting PWM driver configurations for "
                    f"bus {config.bus}, address {config.address}"
                )
            return existing

        driver = PWMFactory.create_pwm_driver(
            bus=self.smbus_manager.get_bus(config.bus),
            config=config.to_dataclass(),
        )
        try:
            driver.set_pwm_freq(config.freq)
        except Exception:
            driver.close()
            raise
        self._pwm_drivers[key] = driver
        self._pwm_driver_configs[key] = config.model_copy(deep=True)
        return driver

    def _make_servo(
        self, servo_config: Union[GPIOAngularServoConfig, AngularServoConfig]
    ) -> ServoService:
        if isinstance(servo_config, AngularServoConfig):
            driver = self._get_pwm_driver(servo_config.driver)

            servo = Servo(
                channel=servo_config.channel,
                driver=driver,
                min_angle=servo_config.min_angle,
                max_angle=servo_config.max_angle,
                min_pulse=servo_config.min_pulse,
                max_pulse=servo_config.max_pulse,
                owns_driver=False,
            )
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
