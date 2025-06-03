from typing import Optional, Union

from app.schemas.robot.battery import BatteryConfig
from app.schemas.robot.distance import UltrasonicConfig
from app.schemas.robot.led import LedConfig
from app.schemas.robot.motors import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    PhaseMotorConfig,
)
from app.schemas.robot.servos import AngularServoConfig, GPIOAngularServoConfig
from app.util.pydantic_helpers import partial_model
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class HardwareConfig(BaseModel):
    """
    The configuration for the robot components and sensors.
    """

    steering_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig, None],
        Field(
            ...,
            title="Steering Servo",
            description="Configuration for the steering servo.",
        ),
    ] = None
    cam_pan_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig, None],
        Field(
            ...,
            title="Camera Pan Servo",
            description="Configuration for the camera pan servo.",
        ),
    ] = None
    cam_tilt_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig, None],
        Field(
            ...,
            title="Camera Tilt Servo",
            description="Configuration for the camera tilt servo.",
        ),
    ] = None

    left_motor: Annotated[
        Union[GPIODCMotorConfig, I2CDCMotorConfig, PhaseMotorConfig, None],
        Field(
            ...,
            title="Left Motor",
            description="Configuration for the left motor.",
        ),
    ] = None
    right_motor: Annotated[
        Union[GPIODCMotorConfig, I2CDCMotorConfig, PhaseMotorConfig, None],
        Field(
            ...,
            title="Right Motor",
            description="Configuration for the right motor.",
        ),
    ] = None

    battery: Annotated[
        Optional[BatteryConfig],
        Field(
            ...,
            title="Battery",
            description="Configuration for the battery.",
        ),
    ] = None

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


@partial_model
class PartialHardwareConfig(HardwareConfig):
    pass


if __name__ == "__main__":
    import json

    with open("config-schema.json", "w") as f:
        json.dump(HardwareConfig.model_json_schema(), f, indent=2)
