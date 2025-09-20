from typing import Optional, Union

from app.core.logger import Logger
from app.schemas.robot.common import EnabledField
from app.schemas.robot.pwm import PWMDriverConfig
from pydantic import BaseModel, Field, model_validator
from robot_hat import MotorDirection
from robot_hat.data_types.config.motor import (
    GPIODCMotorConfig as GPIODCMotorConfigDataclass,
)
from robot_hat.data_types.config.motor import (
    I2CDCMotorConfig as I2CDCMotorConfigDataclass,
)
from robot_hat.data_types.config.motor import (
    PhaseMotorConfig as PhaseMotorConfigDataclass,
)
from typing_extensions import Annotated

logger = Logger(__name__)


MotorDirectionField = Annotated[
    MotorDirection,
    Field(
        default=1,
        ge=-1,
        le=1,
        description="Initial motor direction calibration (+1/-1)",
        json_schema_extra={"type": "motor_direction"},
        examples=[1, -1],
    ),
]


class MotorBaseConfig(BaseModel):
    enabled: EnabledField = True
    calibration_direction: MotorDirectionField
    saved_calibration_direction: Annotated[
        Optional[MotorDirection],
        Field(
            default=1,
            ge=-1,
            le=1,
            description="Saved motor direction calibration (+1/-1)",
            json_schema_extra={
                "type": "integer",
                "props": {"disabled": True, "hidden": True},
            },
            examples=[1, -1],
        ),
    ] = None
    name: Annotated[
        str,
        Field(
            ...,
            title="Name",
            description="Human-readable name for the motor",
            examples=["left", "right"],
        ),
    ]
    max_speed: Annotated[
        int,
        Field(
            ...,
            title="Max speed",
            description="Maximum allowable speed for the motor.",
            examples=[100, 90],
            gt=0,
        ),
    ]

    @model_validator(mode="after")
    def validate_motor_config(self):
        """
        Ensure logical consistency in motor configuration:
        - calibration_direction should be either 1 or -1.
        """
        if self.saved_calibration_direction is None:
            self.saved_calibration_direction = self.calibration_direction

        if self.calibration_direction not in [1, -1]:
            raise ValueError(
                f"`calibration_direction` for motor '{self.name}' must be either 1 or -1."
            )
        return self


class I2CDCMotorConfig(MotorBaseConfig):
    """
    The configuration for the motor, which is controlled via a PWM driver over I²C.
    """

    channel: Annotated[
        Union[str, int],
        Field(
            ...,
            title="PWM channel",
            json_schema_extra={"type": "string_or_number"},
            description="PWM channel number or name.",
            examples=["P0", "P1", "P2", 0, 1, 2],
        ),
    ] = "P0"

    dir_pin: Annotated[
        Union[str, int],
        Field(
            ...,
            title="Direction (phase) pin",
            json_schema_extra={"type": "pin"},
            description="The GPIO pin that the phase (direction) input of the motor driver chip is connected to.",
            examples=["D4", "D5", 23, 24],
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

    def to_dataclass(self) -> I2CDCMotorConfigDataclass:
        return I2CDCMotorConfigDataclass(
            calibration_direction=self.calibration_direction,
            name=self.name,
            max_speed=self.max_speed,
            driver=self.driver.to_dataclass(),
            channel=self.channel,
            dir_pin=self.dir_pin,
        )


class GPIODCMotorConfig(MotorBaseConfig):
    """
    The configuration for the motor, which is controlled without I²C.

    It is suitable when the motor driver board, for example, a Waveshare/MC33886-based
    module, does not require or use an external PWM driver and is controlled entirely
    through direct GPIO calls.
    """

    forward_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            title="Forward PIN",
            json_schema_extra={"type": "pin"},
            description="The GPIO pin that the forward input of the motor driver chip "
            "is connected to.",
        ),
    ]
    backward_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            json_schema_extra={"type": "pin"},
            title="Backward PIN",
            description="The GPIO pin that the forward input of the motor driver chip "
            "is connected to.",
        ),
    ]
    enable_pin: Annotated[
        Optional[Union[int, str]],
        Field(
            ...,
            title="Enable PIN",
            json_schema_extra={"type": "pin"},
            description="The GPIO pin that enables the motor. "
            "Required for **some** motor controller boards.",
        ),
    ] = None
    pwm: Annotated[
        bool,
        Field(
            ...,
            title="PWM",
            description="Whether to construct PWM Output Device instances for "
            "the motor controller pins, allowing both direction and speed control.",
        ),
    ] = True

    def to_dataclass(self) -> GPIODCMotorConfigDataclass:
        return GPIODCMotorConfigDataclass(
            calibration_direction=self.calibration_direction,
            name=self.name,
            max_speed=self.max_speed,
            forward_pin=self.forward_pin,
            backward_pin=self.backward_pin,
            enable_pin=self.enable_pin,
            pwm=self.pwm,
        )


class PhaseMotorConfig(MotorBaseConfig):
    """
    The configuration for the a phase/enable motor driver board.
    """

    phase_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            title="Enable PIN",
            json_schema_extra={"type": "pin"},
            description="GPIO pin for the phase/direction. ",
        ),
    ]
    pwm: Annotated[
        bool,
        Field(
            ...,
            title="PWM",
            description="Whether to construct PWM Output Device instances for "
            "the motor controller pins, allowing both direction and speed control.",
        ),
    ] = True

    enable_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            title="Enable PIN",
            json_schema_extra={"type": "pin"},
            description="The GPIO pin that enables the motor. "
            "Required for **some** motor controller boards.",
        ),
    ]

    def to_dataclass(self) -> PhaseMotorConfigDataclass:
        return PhaseMotorConfigDataclass(
            calibration_direction=self.calibration_direction,
            name=self.name,
            max_speed=self.max_speed,
            phase_pin=self.phase_pin,
            pwm=self.pwm,
            enable_pin=self.enable_pin,
        )


if __name__ == "__main__":
    from pprint import pp

    print("\n\033[1m\033[32m Phase Motor \033[0m\033[36mJSON schema:\033[0m")
    pp(PhaseMotorConfig.model_json_schema())
    print("\n\033[1m\033[32m GPIO DC MotorConfig \033[0m\033[36mJSON schema:\033[0m")
    pp(GPIODCMotorConfig.model_json_schema())
    print("\n\033[1m\033[32m I2C DC MotorConfig \033[0m\033[36mJSON schema:\033[0m")
    pp(I2CDCMotorConfig.model_json_schema())
