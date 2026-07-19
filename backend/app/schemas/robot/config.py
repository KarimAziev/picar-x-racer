from typing import List, Literal, Optional, Union

from app.schemas.robot.avoid_obstacles import AvoidParams
from app.schemas.robot.battery import BatteryConfig
from app.schemas.robot.distance import UltrasonicConfig
from app.schemas.robot.led import LedConfig
from app.schemas.robot.motors import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    PhaseMotorConfig,
)
from app.schemas.robot.motion_control import MotionControlConfig
from app.schemas.robot.servos import AngularServoConfig, GPIOAngularServoConfig
from app.schemas.robot.servos import (
    cross_field_validators as servo_cross_field_validators,
)
from app.util.pydantic_helpers import partial_model
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated


class HardwareConfig(BaseModel):
    """
    The configuration for the robot components and sensors.
    """

    schema_version: Annotated[
        Literal[3],
        Field(
            title="Schema version",
            json_schema_extra={"props": {"disabled": True, "hidden": True}},
        ),
    ] = 3

    motion_control: Annotated[
        MotionControlConfig,
        Field(
            title="Motion control",
            description=(
                "Physical speed calibration and watchdog settings for the "
                "single-writer motion runtime."
            ),
        ),
    ] = MotionControlConfig()

    steering_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig],
        Field(
            ...,
            title="Steering Servo",
            description="Configuration for the steering servo.",
            json_schema_extra={
                "cross_field_validation": servo_cross_field_validators,
            },
        ),
    ]
    cam_pan_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig],
        Field(
            ...,
            title="Camera Pan Servo",
            description="Configuration for the camera pan servo.",
            json_schema_extra={
                "cross_field_validation": servo_cross_field_validators,
            },
        ),
    ]
    cam_tilt_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig],
        Field(
            ...,
            title="Camera Tilt Servo",
            description="Configuration for the camera tilt servo.",
        ),
    ]

    motors: Annotated[
        List[Union[GPIODCMotorConfig, I2CDCMotorConfig, PhaseMotorConfig]],
        Field(
            ...,
            title="Motors",
            description=(
                "Motor configuration. One configured motor uses SingleMotorService; "
                "two configured motors use MotorService."
            ),
            min_length=1,
            max_length=2,
            json_schema_extra={
                "props": {
                    "addLabel": "Add motor",
                    "itemLabel": "Motor",
                }
            },
        ),
    ]

    batteries: Annotated[
        List[BatteryConfig],
        Field(
            ...,
            title="Batteries",
            description="Configurations for monitored batteries and power supplies.",
            json_schema_extra={
                "uniqueItemProperty": "name",
                "props": {
                    "addLabel": "Add battery",
                    "itemLabel": "Battery",
                },
            },
        ),
    ] = Field(default_factory=list)

    ultrasonic: Annotated[
        Union[UltrasonicConfig, None],
        Field(
            ...,
            title="Distance sensor",
            description="Configuration for the distance sensor.",
        ),
    ] = None

    led: Annotated[
        Optional[LedConfig],
        Field(
            ...,
            title="LED",
            description="Configuration for the LED.",
        ),
    ] = None

    avoid_obstacles_params: Annotated[
        AvoidParams,
        Field(
            ...,
            title="Avoid Obstacles Config",
            description="Parameters for Avoid Obstacles Mode",
        ),
    ] = AvoidParams()

    @model_validator(mode="after")
    def validate_unique_battery_names(self) -> "HardwareConfig":
        names = [battery.name.strip().casefold() for battery in self.batteries]
        if len(names) != len(set(names)):
            raise ValueError("Battery names must be unique")
        return self


@partial_model
class PartialHardwareConfig(HardwareConfig):
    pass


if __name__ == "__main__":
    import json

    with open("config-schema.json", "w") as f:
        json.dump(HardwareConfig.model_json_schema(), f, indent=2)
