from typing import Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from robot_hat import ServoCalibrationMode
from typing_extensions import Annotated


class ServoConfig(BaseModel):
    name: str = Field(
        ...,
        description="A name for the servo (useful for debugging/logging). ",
        examples=["Steering Direction", "Camera Pan"],
    )
    calibration_offset: float = Field(
        0.0,
        description="A calibration offset for fine-tuning servo angles.",
        examples=[0.0, 0.4, -4.2],
    )
    min_angle: int = Field(
        ...,
        description="Minimum allowable angle for the servo",
        examples=[-30, -45],
    )
    max_angle: int = Field(
        ...,
        description="Maximum allowable angle for the servo",
        examples=[30, 45],
    )
    calibration_mode: Annotated[
        ServoCalibrationMode,
        Field(
            ServoCalibrationMode.NEGATIVE,
            description="Specifies how calibration offsets are applied.",
            examples=[
                ServoCalibrationMode.SUM.value,
                ServoCalibrationMode.NEGATIVE.value,
            ],
        ),
    ]

    servo_pin: Union[str, int] = Field(
        ...,
        description="PWM channel number or name.",
        examples=["P0", "P1", "P2", 0, 1, 2],
    )

    @model_validator(mode="after")
    def validate_servo_config(self):
        """
        Ensure logical consistency in servo configuration:
        - min_angle should be less than max_angle
        - calibration_offset should be within a reasonable range (-360 to 360)
        """
        if self.min_angle >= self.max_angle:
            raise ValueError(
                f"`min_angle` must be less than `max_angle` for {self.name}."
            )
        if not -360 <= self.calibration_offset <= 360:
            raise ValueError(
                f"Calibration offset {self.calibration_offset} for {self.name} must be in the range [-360, 360]."
            )
        return self


class MotorConfig(BaseModel):
    name: str = Field(
        ...,
        description="Human-readable name for the motor",
        examples=["left", "right"],
    )
    calibration_direction: Literal[1, -1] = Field(
        ...,
        description="Initial motor direction calibration (+1/-1)",
        examples=[1, -1],
    )
    calibration_speed_offset: float = Field(
        0.0,
        description="Initial motor speed calibration offset",
        examples=[0.0, 0.1],
    )
    max_speed: int = Field(
        ...,
        description="Maximum allowable speed for the motor.",
        examples=[100, 90],
    )
    period: int = Field(
        4095,
        description="PWM period for speed control",
        examples=[4095],
    )
    prescaler: int = Field(
        10,
        description="PWM prescaler for speed control",
        examples=[10],
    )
    dir_pin: Union[str, int] = Field(
        ...,
        description="Direction PIN identifier, either as a GPIO pin number or a named string.",
        examples=["D4", "D5", 23, 24],
    )
    pwm_pin: Union[str, int] = Field(
        ...,
        description="PWM channel number or name.",
        examples=["P12", "P13", 12, 13],
    )

    @model_validator(mode="after")
    def validate_motor_config(self):
        """
        Ensure logical consistency in motor configuration:
        - max_speed should be a positive integer.
        - calibration_direction should be either 1 or -1.
        """
        if self.max_speed <= 0:
            raise ValueError(
                f"`max_speed` must be greater than 0 for motor '{self.name}'."
            )
        if self.calibration_direction not in [1, -1]:
            raise ValueError(
                f"`calibration_direction` for motor '{self.name}' must be either 1 or -1."
            )
        return self


class ConfigSchema(BaseModel):
    cam_pan_servo: ServoConfig
    cam_tilt_servo: ServoConfig
    steering_servo: ServoConfig
    left_motor: MotorConfig
    right_motor: MotorConfig

    @model_validator(mode="after")
    def validate_overall_config(self):
        """
        Ensure logical consistency across the entire configuration.
        - Duplicate pin names between motors and servos should not exist.
        """
        pins = []
        for servo in [self.cam_pan_servo, self.cam_tilt_servo, self.steering_servo]:
            pins.append(servo.servo_pin)
        for motor in [self.left_motor, self.right_motor]:
            pins.extend([motor.dir_pin, motor.pwm_pin])

        if len(pins) != len(set(pins)):
            raise ValueError("Duplicate pin identifiers found in the configuration.")

        return self


class CalibrationConfig(BaseModel):
    """
    A model representing the calibration configuration.
    """

    steering_servo_offset: float = Field(
        0.0,
        description="A calibration offset for fine-tuning servo direction angles.",
        examples=[-1.5],
    )
    cam_pan_servo_offset: float = Field(
        0.0,
        description="A calibration offset for fine-tuning camera pan servo angles.",
        examples=[-0.9],
    )

    cam_tilt_servo_offset: float = Field(
        0.0,
        description="A calibration offset for fine-tuning camera tilt servo angles.",
        examples=[1.3],
    )

    left_motor_direction: Annotated[
        int,
        Field(
            1,
            strict=True,
            ge=-1,
            le=1,
            description="Initial motor direction calibration (+1/-1)",
            examples=[1],
        ),
    ]

    right_motor_direction: Annotated[
        int,
        Field(
            1,
            strict=True,
            ge=-1,
            le=1,
            description="Initial motor direction calibration (+1/-1)",
            examples=[1],
        ),
    ]

    @field_validator("left_motor_direction", "right_motor_direction")
    def validate_motor_direction(cls, value):
        if value not in (-1, 1):
            raise ValueError("Motor direction must be either 1 or -1.")
        return value
