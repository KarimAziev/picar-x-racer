from typing import List, Optional

from app.config.paths import PX_CALIBRATION_FILE
from app.util.constrain import constrain
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from robot_hat import (
    ADC,
    FileDB,
    Grayscale,
    MotorConfig,
    MotorController,
    MotorFabric,
    Servo,
)


class PicarxAdapter(metaclass=SingletonMeta):
    DEFAULT_CLIFF_REF = [500, 500, 500]
    DIR_MIN = -30
    DIR_MAX = 30
    MAX_SPEED = 100
    CAM_PAN_MIN = -90
    CAM_PAN_MAX = 90
    CAM_TILT_MIN = -35
    CAM_TILT_MAX = 65

    def __init__(
        self,
        servo_pins: list[str] = ["P0", "P1", "P2"],
        motor_dir_pins: list[str] = ["D4", "D5"],
        motor_speed_pins: list[str] = ["P12", "P13"],
        grayscale_pins: list[str] = ["A0", "A1", "A2"],
        config_file: str = PX_CALIBRATION_FILE,
    ):
        self.logger = Logger(name=__name__)
        self.config = FileDB(config_file)

        # --------- servos init ---------
        self.cam_pan, self.cam_tilt, self.dir_servo_pin = [
            Servo(pin) for pin in servo_pins
        ]
        # Get calibration values
        self.dir_cali_val = self.config.get_value_with("picarx_dir_servo", float) or 0.0
        self.dir_current_angle = 0.0

        self.cam_pan_cali_val = (
            self.config.get_value_with("picarx_cam_pan_servo", float) or 0.0
        )

        self.cam_tilt_cali_val = (
            self.config.get_value_with("picarx_cam_tilt_servo", float) or 0.0
        )

        # Set servos to init angle
        self.dir_servo_pin.angle(self.dir_cali_val)
        self.cam_pan.angle(self.cam_pan_cali_val)
        self.cam_tilt.angle(self.cam_tilt_cali_val)

        # --------- motors init ---------

        cali_dir_value = self.config.get_list_value_with("picarx_dir_motor", int)
        left_motor, right_motor = MotorFabric.create_motor_pair(
            MotorConfig(
                dir_pin=motor_dir_pins[0],
                pwm_pin=motor_speed_pins[0],
                calibration_direction=(
                    cali_dir_value[0] if len(cali_dir_value) == 2 else 1
                ),
                max_speed=self.MAX_SPEED,
                name="LeftMotor",
            ),
            MotorConfig(
                dir_pin=motor_dir_pins[1],
                pwm_pin=motor_speed_pins[1],
                calibration_direction=(
                    cali_dir_value[1] if len(cali_dir_value) == 2 else 1
                ),
                max_speed=self.MAX_SPEED,
                name="RightMotor",
            ),
        )

        self.motor_controller = MotorController(
            left_motor=left_motor, right_motor=right_motor
        )

        # --------- grayscale module init ---------
        adc0, adc1, adc2 = [ADC(pin) for pin in grayscale_pins]

        self.grayscale = Grayscale(adc0, adc1, adc2)
        # Get reference
        self.line_reference = (
            self.config.get_list_value_with("line_reference", int)
            or self.grayscale.reference
        )
        self.cliff_reference = (
            self.config.get_list_value_with("cliff_reference", int)
            or self.DEFAULT_CLIFF_REF
        )

        self.grayscale.reference = self.line_reference

    def dir_servo_calibrate(self, value: float) -> None:
        """
        Calibrate the steering direction servo.

        Args:
           value (float): Calibration value
        """
        self.dir_cali_val = value
        self.config.set("picarx_dir_servo", str(value))
        self.dir_servo_pin.angle(value)

    def set_dir_servo_angle(self, value: float) -> None:
        """
        Set the servo angle for the vehicle's steering direction.

        Args:
           value (int): Desired angle
        """
        original_value = self.dir_current_angle
        self.dir_current_angle = constrain(value, self.DIR_MIN, self.DIR_MAX)
        angle_value = self.dir_current_angle + self.dir_cali_val

        self.logger.debug(
            "Direction angle from %s to %s (calibrated %s)",
            original_value,
            self.dir_current_angle,
            angle_value,
        )
        self.dir_servo_pin.angle(angle_value)

    def cam_pan_servo_calibrate(self, value: int) -> None:
        """
        Calibrate the camera pan servo.

        Args:
           value (int): Calibration value
        """
        self.cam_pan_cali_val = value
        self.config.set("picarx_cam_pan_servo", str(value))
        self.cam_pan.angle(value)

    def cam_tilt_servo_calibrate(self, value: int) -> None:
        """
        Calibrate the camera tilt servo.

        Args:
           value (int): Calibration value
        """
        self.logger.info("Calibrating camera tilt servo with value %s", value)
        self.cam_tilt_cali_val = value
        self.config.set("picarx_cam_tilt_servo", str(value))
        self.cam_tilt.angle(value)

    def set_cam_pan_angle(self, value: int) -> None:
        """
        Set the camera pan angle.

        Args:
           value (int): Desired angle
        """

        constrained_value = constrain(value, self.CAM_PAN_MIN, self.CAM_PAN_MAX)
        angle_value = -1 * (constrained_value + -1 * self.cam_pan_cali_val)

        self.logger.debug(
            "Setting camera pan angle: '%s', adjusted: '%s' with offset '%s')",
            value,
            angle_value,
            self.cam_pan_cali_val,
        )
        self.cam_pan.angle(angle_value)

    def set_cam_tilt_angle(self, value: int) -> None:
        """
        Set the camera tilt angle.

        Args:
           value (int): Desired angle
        """
        constrained_value = constrain(value, self.CAM_TILT_MIN, self.CAM_TILT_MAX)
        angle_value = -1 * (constrained_value + -1 * self.cam_tilt_cali_val)

        self.logger.debug("Setting camera tilt angle to '%s'", angle_value)
        self.cam_tilt.angle(angle_value)

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

        if motor == 1:
            self.motor_controller.update_left_motor_calibration_direction(
                value, persist=True
            )
        else:
            self.motor_controller.update_right_motor_calibration_direction(
                value, persist=True
            )

        self.config.set(
            "picarx_dir_motor",
            str(
                [
                    self.motor_controller.left_motor.calibration_direction,
                    self.motor_controller.right_motor.calibration_direction,
                ]
            ),
        )

    def move(self, speed: int, direction: int) -> None:
        """
        Move the robot forward or backward with steering based on the current angle.

        Args:
        - speed (int): The base speed at which to move.
        - direction (int): 1 for forward, -1 for backward.
        """
        current_angle = self.dir_current_angle
        abs_current_angle = min(abs(current_angle), self.DIR_MAX)
        return self.motor_controller.move(speed, direction, int(abs_current_angle))

    def forward(self, speed: int) -> None:
        """
        Move the robot forward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.
        """
        self.logger.debug("Forward: 100/%s", speed)
        self.move(speed, direction=1)

    def backward(self, speed: int) -> None:
        """
        Move the robot backward with steering based on the current angle.

        Args:
           speed (int): The base speed at which to move.
        """
        self.logger.debug("Backward: 100/%s", speed)
        self.move(speed, direction=-1)

    def stop(self) -> None:
        """
        Stop the motors by setting the motor speed pins' pulse width to 0 twice, with a short delay between attempts.
        """
        return self.motor_controller.stop_all()

    def set_grayscale_reference(self, value: List[int]) -> None:
        """
        Sets and save the reference values for the grayscale sensors.
        """
        self.grayscale.reference = value
        self.line_reference = self.grayscale.reference
        self.config.set("line_reference", str(self.line_reference))

    def get_grayscale_data(self) -> List[int]:
        """
        Reads grayscale intensity values from all three channels.

        Returns:
            A list of grayscale intensity values for all channels.
        """
        return self.grayscale.read_all()

    def get_line_status(self, gm_val_list: Optional[List[int]] = None) -> List[int]:
        """
        Reads the status of the lines based on current reference values. Status is
        calculated as 0 for white and 1 for black.

        Args:
            datas: List of grayscale data to process. If not provided, grayscale data is read directly from the sensors.

        Returns:
            A list of statuses for each channel, where 0 represents white
            and 1 represents black.

        Raises:
            ValueError: If the reference values are not set.
        """
        return self.grayscale.read_status(gm_val_list)

    def set_line_reference(self, value: List[int]):
        self.set_grayscale_reference(value)

    def get_cliff_status(self, gm_val_list: List[int]) -> bool:
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

    def set_cliff_reference(self, value: List[int]) -> None:
        """
        Sets the reference values for detecting cliffs based on grayscale sensor readings.
        """
        if isinstance(value, list) and len(value) == 3:
            self.cliff_reference = value
            self.config.set("cliff_reference", str(self.cliff_reference))
        else:
            raise ValueError("cliff reference must be a 1*3 list")
