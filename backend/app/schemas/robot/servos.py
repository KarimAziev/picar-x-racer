
from typing import  Union
from app.core.logger import Logger
from app.schemas.robot.common import EnabledField
from app.schemas.robot.pwm import PWMDriverConfig
from pydantic import BaseModel, Field, model_validator
from robot_hat import ServoCalibrationMode
from typing_extensions import Annotated

logger = Logger(__name__)


class ServoConfig(BaseModel):
    enabled: EnabledField = True
    name: Annotated[
        str,
        Field(
            ...,
            description="A name for the servo (useful for debugging/logging). ",
            examples=["Steering Direction", "Camera Pan"],
        ),
    ]
    calibration_offset: Annotated[
        float,
        Field(
            0.0,
            description="A calibration offset for fine-tuning servo angles.",
            examples=[0.0, 0.4, -4.2],
        ),
    ]
    min_angle: Annotated[
        int,
        Field(
            ...,
            description="Minimum allowable angle for the servo",
            examples=[-30, -45],
        ),
    ] = -30
    max_angle: Annotated[
        int,
        Field(
            ...,
            description="Maximum allowable angle for the servo",
            examples=[30, 45],
        ),
    ] = 30
    dec_step: Annotated[
        int,
        Field(
            ...,
            description="The step value by which the servo's angle decreases. Must be a negative integer.",
            examples=[-5, -10],
            lt=0,
        ),
    ] = -5
    inc_step: Annotated[
        int,
        Field(
            ...,
            description="The step value by which the servo's angle increases. Must be a positive integer.",
            gt=0,
            examples=[5, 2],
        ),
    ] = 5
    min_pulse: Annotated[
        int,
        Field(
            ...,
            description="The pulse width in microseconds (µs) corresponding to the servo's minimum position",
            examples=[500],
        ),
    ] = 500

    max_pulse: Annotated[
        int,
        Field(
            ...,
            description="The maximum pulse width in microseconds (µs) corresponding to the servo's maximum position.",
            examples=[2500],
        ),
    ] = 2500

    calibration_mode: Annotated[
        ServoCalibrationMode,
        Field(
            ...,
            title="Calibration mode",
            description="Specifies how calibration offsets are applied.",
            examples=[
                ServoCalibrationMode.SUM.value,
                ServoCalibrationMode.NEGATIVE.value,
            ],
            json_schema_extra={
                "tooltipHelp": "Specifies how calibration offsets are applied.",
                "title": "Calibration mode",
            },
        ),
    ] = ServoCalibrationMode.NEGATIVE

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


class AngularServoConfig(ServoConfig):
    """Configuration for servos driven via external PWM driver or HAT via I²C."""

    channel: Annotated[
        Union[str, int],
        Field(
            ...,
            title="PWM channel",
            json_schema_extra={"type": "string_or_number"},
            description="PWM channel number or name.",
            examples=["P0", "P1", "P2", 0, 1, 2],
        ),
    ]
    driver: Annotated[
        PWMDriverConfig,
        Field(
            ...,
            title="PWM driver",
            description="The PWM driver chip configuration.",
        ),
    ] = PWMDriverConfig()


class GPIOAngularServoConfig(ServoConfig):
    """
    Configuration for servos driven directly via Raspberry Pi GPIO (without I²C and external PWM driver).
    """

    pin: Annotated[
        Union[str, int],
        Field(
            ...,
            json_schema_extra={"type": "string_or_number"},
            title="GPIO PIN",
            description="Broadcom (BCM) pin number for the GPIO pins, as opposed to physical (BOARD) numbering.",
            examples=["GPIO17", "GPIO27", 1, 2],
        ),
    ]


if __name__ == "__main__":
    from pprint import pp

    print(
        "\n\033[1m\033[32m GPIO Angular Servo Config \033[0m\033[36mJSON schema:\033[0m"
    )
    pp(GPIOAngularServoConfig.model_json_schema())

    print("\n\033[1m\033[32m Angular Servo Config \033[0m\033[36mJSON schema:\033[0m")
    pp(AngularServoConfig.model_json_schema())
