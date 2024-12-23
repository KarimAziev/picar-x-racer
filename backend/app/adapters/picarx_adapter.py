from app.config.paths import PX_CALIBRATION_FILE
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from robot_hat import (
    FileDB,
    MotorConfig,
    MotorController,
    MotorFabric,
    Servo,
    constrain,
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

    @staticmethod
    def calc_angle(
        value: float, min_value: float, max_value: float, calibration_value: float
    ) -> float:
        """
        Calculate and return a constrained and adjusted angle value based on input parameters.
        """
        constrained_value = constrain(value, min_value, max_value)
        return -1 * (constrained_value + -1 * calibration_value)

    def set_cam_pan_angle(self, value: int) -> None:
        """
        Set the camera pan angle.

        Args:
           value (int): Desired angle
        """

        adjusted_value = PicarxAdapter.calc_angle(
            value, self.CAM_PAN_MIN, self.CAM_PAN_MAX, self.cam_pan_cali_val
        )
        self.cam_pan.angle(adjusted_value)

    def set_cam_tilt_angle(self, value: int) -> None:
        """
        Set the camera tilt angle.

        Args:
           value (int): Desired angle
        """
        adjusted_value = PicarxAdapter.calc_angle(
            value, self.CAM_TILT_MIN, self.CAM_TILT_MAX, self.cam_tilt_cali_val
        )
        self.cam_tilt.angle(adjusted_value)

    def motor_direction_calibrate(self, motor: int, value: int):
        """
        Set motor direction calibration value.

        Args:
           motor (int): Motor index (1 for left motor, 2 for right motor)
           value (int): Calibration value (1 or -1)
        """
        if motor not in (1, 2):
            raise ValueError("Motor index must be 1 (left) or 2 (right).")

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
        abs_current_angle = min(abs(self.dir_current_angle), self.DIR_MAX)
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
