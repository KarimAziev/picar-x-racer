from typing import List, Literal, Optional, Union

from app.schemas.robot.avoid_obstacles import AvoidParams
from app.schemas.robot.battery import BatteryConfig
from app.schemas.robot.distance import UltrasonicConfig
from app.schemas.robot.led import LedConfig
from app.schemas.robot.localization_sensors import (
    AS5048AEncoderConfig,
    AS5600LEncoderConfig,
    LocalizationSensorsConfig,
)
from app.schemas.robot.mapping import LocalMappingConfig
from app.schemas.robot.motors import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    PhaseMotorConfig,
)
from app.schemas.robot.motion_control import MotionControlConfig
from app.schemas.robot.odometry import AckermannOdometryConfig
from app.schemas.robot.pose_estimation import PoseEstimationConfig
from app.schemas.robot.safety import LidarSafetyConfig
from app.schemas.robot.simulation import CoherentSimulationConfig
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
        Literal[6],
        Field(
            title="Schema version",
            json_schema_extra={"props": {"disabled": True, "hidden": True}},
        ),
    ] = 6

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

    ackermann_odometry: Annotated[
        AckermannOdometryConfig,
        Field(
            title="Ackermann odometry",
            description="Measured chassis geometry and drive-encoder calibration.",
        ),
    ] = AckermannOdometryConfig()

    localization_sensors: Annotated[
        LocalizationSensorsConfig,
        Field(
            title="Localization sensors",
            description=(
                "Disabled-by-default LiDAR, IMU, and drive-encoder acquisition."
            ),
        ),
    ] = LocalizationSensorsConfig()

    lidar_safety: Annotated[
        LidarSafetyConfig,
        Field(
            title="LiDAR forward safety",
            description="Fail-safe front-sector speed limiting and stop behavior.",
        ),
    ] = LidarSafetyConfig()

    local_mapping: Annotated[
        LocalMappingConfig,
        Field(
            title="Local occupancy mapping",
            description="LiDAR ray integration in the odom frame.",
        ),
    ] = LocalMappingConfig()

    coherent_simulation: Annotated[
        CoherentSimulationConfig,
        Field(
            title="Coherent simulation",
            description=(
                "Whole-vehicle Ackermann simulation driven by final motion commands."
            ),
        ),
    ] = CoherentSimulationConfig()

    pose_estimation: Annotated[
        PoseEstimationConfig,
        Field(
            title="Pose estimation",
            description=(
                "Fuse locally smooth wheel odometry with fresh IMU yaw rate and "
                "optional external pose corrections."
            ),
        ),
    ] = PoseEstimationConfig()

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
    def validate_hardware_relationships(self) -> "HardwareConfig":
        simulation_enabled = bool(
            self.coherent_simulation is not None and self.coherent_simulation.enabled
        )
        if "batteries" in self.model_fields_set:
            if self.batteries is None:
                raise ValueError("Batteries must be a list")

            names = [battery.name.strip().casefold() for battery in self.batteries]
            if len(names) != len(set(names)):
                raise ValueError("Battery names must be unique")

        # PartialHardwareConfig inherits this validator, so only validate a
        # relationship here when both sides were supplied. SettingsService
        # validates the merged, complete HardwareConfig before activation.
        if self.lidar_safety is not None and self.lidar_safety.enabled:
            if self.motion_control is not None and not self.motion_control.enabled:
                raise ValueError("LiDAR safety requires motion control to be enabled")
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.lidar.enabled
            ):
                raise ValueError(
                    "LiDAR safety requires the LiDAR publisher to be enabled"
                )
        if self.local_mapping is not None and self.local_mapping.enabled:
            if (
                self.ackermann_odometry is not None
                and not self.ackermann_odometry.enabled
            ):
                raise ValueError("local mapping requires Ackermann odometry")
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.lidar.enabled
            ):
                raise ValueError("local mapping requires the LiDAR publisher")
        if self.ackermann_odometry is not None and self.ackermann_odometry.enabled:
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.encoder.enabled
                and not simulation_enabled
            ):
                raise ValueError(
                    "Ackermann odometry requires drive encoders or coherent simulation"
                )
            if self.motion_control is not None and not self.motion_control.enabled:
                raise ValueError(
                    "Ackermann odometry requires motion control steering state"
                )
            known_resolutions = (
                {
                    16_384 if isinstance(sensor, AS5048AEncoderConfig) else 4_096
                    for sensor in self.localization_sensors.encoder.sensors
                    if isinstance(sensor, (AS5048AEncoderConfig, AS5600LEncoderConfig))
                }
                if not simulation_enabled and self.localization_sensors is not None
                else set()
            )
            if len(known_resolutions) > 1:
                raise ValueError(
                    "Ackermann odometry cannot combine rear encoders with different "
                    "native tick resolutions"
                )
            if known_resolutions:
                expected_ticks = next(iter(known_resolutions))
                if (
                    self.ackermann_odometry.encoder_ticks_per_revolution
                    != expected_ticks
                ):
                    raise ValueError(
                        "Ackermann odometry encoder_ticks_per_revolution must be "
                        f"{expected_ticks} for the configured magnetic encoder"
                    )
        if simulation_enabled:
            if self.motion_control is not None and not self.motion_control.enabled:
                raise ValueError("coherent simulation requires motion control")
            if (
                self.ackermann_odometry is not None
                and not self.ackermann_odometry.enabled
            ):
                raise ValueError("coherent simulation requires Ackermann odometry")
        if self.pose_estimation is not None and self.pose_estimation.enabled:
            if (
                self.ackermann_odometry is not None
                and not self.ackermann_odometry.enabled
            ):
                raise ValueError("pose estimation requires Ackermann odometry")
        if (
            self.pose_estimation is not None
            and self.pose_estimation.simulation_scan_matching.enabled
        ):
            if not self.pose_estimation.enabled:
                raise ValueError("simulation scan matching requires pose estimation")
            if self.coherent_simulation is not None and not simulation_enabled:
                raise ValueError(
                    "simulation scan matching requires coherent simulation"
                )
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.lidar.enabled
            ):
                raise ValueError(
                    "simulation scan matching requires the LiDAR publisher"
                )
        return self


@partial_model
class PartialHardwareConfig(HardwareConfig):
    pass


if __name__ == "__main__":
    import json

    with open("config-schema.json", "w") as f:
        json.dump(HardwareConfig.model_json_schema(), f, indent=2)
