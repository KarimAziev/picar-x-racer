from typing import List, Literal, Optional, Union

from app.schemas.robot.avoid_obstacles import AvoidParams
from app.schemas.robot.auxiliary_sensors import AuxiliarySensorsConfig
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
from app.schemas.robot.navigation import NavigationConfig
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

    navigation: NavigationConfig = Field(
        default_factory=NavigationConfig,
        title="Navigation geometry and policy",
        description="Choose how routes are planned and enter the robot body dimensions. Measure the axle spacing separately under Ackermann odometry. Save and restart the backend to apply changes.",
    )

    schema_version: Annotated[
        Literal[8],
        Field(
            title="Schema version",
            description=(
                "Internal hardware-configuration format version maintained by "
                "ordered migrations."
            ),
            json_schema_extra={"props": {"disabled": True, "hidden": True}},
        ),
    ] = 8

    motion_control: Annotated[
        MotionControlConfig,
        Field(
            title="Motion control",
            description=(
                "Converts driving commands into motor speed and steering angle. Enter measured forward and reverse speeds before enabling. Required for Ackermann odometry. Save and restart the backend to apply changes."
            ),
        ),
    ] = MotionControlConfig()

    ackermann_odometry: Annotated[
        AckermannOdometryConfig,
        Field(
            title="Ackermann odometry",
            description=(
                "Tracks distance travelled and turns using wheel encoders and steering angle. First configure Motion control and Localization sensors > Drive encoders, then enter the wheel measurements below. Save and restart the backend after enabling."
            ),
        ),
    ] = AckermannOdometryConfig()

    localization_sensors: Annotated[
        LocalizationSensorsConfig,
        Field(
            title="Localization sensors",
            description=(
                "Set up the sensors that measure nearby obstacles, wheel movement, and turning. LiDAR and drive encoders are needed for mapping on the real robot; the IMU can improve turn estimates."
            ),
        ),
    ] = LocalizationSensorsConfig()

    auxiliary_sensors: Annotated[
        AuxiliarySensorsConfig,
        Field(
            title="Auxiliary sensors",
            description=(
                "Add temperature, humidity, pressure, or magnetic-field sensors to display their readings. These sensors are optional for mapping."
            ),
        ),
    ] = AuxiliarySensorsConfig()

    lidar_safety: Annotated[
        LidarSafetyConfig,
        Field(
            title="LiDAR directional safety",
            description="Automatically slow or stop driving toward nearby obstacles. First enable Motion control and Localization sensors > LiDAR sensor. Set stopping distances that allow room for the whole robot. Restart the backend after enabling.",
        ),
    ] = LidarSafetyConfig()

    local_mapping: Annotated[
        LocalMappingConfig,
        Field(
            title="Local occupancy mapping",
            description="Build a top-down map of free space and obstacles as you drive. First enable Motion control, Localization sensors > LiDAR sensor and Drive encoders, and Ackermann odometry. Then enable mapping, save, and restart the backend. Mapping does not start driving.",
        ),
    ] = LocalMappingConfig()

    coherent_simulation: Annotated[
        CoherentSimulationConfig,
        Field(
            title="Coherent simulation",
            description=(
                "Drive a virtual robot in a simulated room, with physical motors isolated. Requires calibrated Motion control and Ackermann odometry. Configure both and enable simulation in one save using the bottom Save button."
            ),
        ),
    ] = CoherentSimulationConfig()

    pose_estimation: Annotated[
        PoseEstimationConfig,
        Field(
            title="Pose estimation",
            description=(
                "Estimate where the robot is and which way it faces. Requires Ackermann odometry; an enabled IMU helps track turns. Optional LiDAR matching corrects the estimate against a map."
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
                    "typeLabel": "Motor type",
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
            title="Obstacle avoidance",
            description="Distance thresholds and motion behavior for obstacle mode.",
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
                raise ValueError(
                    "To enable LiDAR directional safety, open Robot > Motion control, enter the measured forward and reverse speeds, enable it, and save."
                )
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.lidar.enabled
            ):
                raise ValueError(
                    "To enable LiDAR directional safety, open Robot > Localization sensors > LiDAR sensor, configure the sensor, enable it, and save."
                )
        if self.local_mapping is not None and self.local_mapping.enabled:
            if (
                self.ackermann_odometry is not None
                and not self.ackermann_odometry.enabled
            ):
                raise ValueError(
                    "To enable Local occupancy mapping, first configure and enable Robot > Ackermann odometry. It needs Motion control and drive encoders on a real robot."
                )
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.lidar.enabled
            ):
                raise ValueError(
                    "To enable Local occupancy mapping, open Robot > Localization sensors > LiDAR sensor, configure the sensor, enable it, and save."
                )
        if self.ackermann_odometry is not None and self.ackermann_odometry.enabled:
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.encoder.enabled
                and not simulation_enabled
            ):
                raise ValueError(
                    "To enable Ackermann odometry on a real robot, configure and enable Robot > Localization sensors > Drive encoders. For a virtual robot, enable Coherent simulation in the same save using the bottom Save button."
                )
            if self.motion_control is not None and not self.motion_control.enabled:
                raise ValueError(
                    "To enable Ackermann odometry, open Robot > Motion control, enter the measured forward and reverse speeds, enable it, and save. Odometry uses its steering angle to calculate turns. Restart the backend after setup."
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
                        "Under Robot > Ackermann odometry, Encoder ticks per revolution must be "
                        f"{expected_ticks} for the configured magnetic encoder"
                    )
        if simulation_enabled:
            if self.motion_control is not None and not self.motion_control.enabled:
                raise ValueError(
                    "To enable Coherent simulation, configure and enable Robot > Motion control. Enter the measured maximum forward and reverse speeds."
                )
            if (
                self.ackermann_odometry is not None
                and not self.ackermann_odometry.enabled
            ):
                raise ValueError(
                    "To enable Coherent simulation, configure and enable Robot > Ackermann odometry. Save both sections together with the bottom Save button."
                )
        if self.pose_estimation is not None and self.pose_estimation.enabled:
            if (
                self.ackermann_odometry is not None
                and not self.ackermann_odometry.enabled
            ):
                raise ValueError(
                    "To enable Pose estimation, first configure and enable Robot > Ackermann odometry."
                )
        if (
            self.pose_estimation is not None
            and self.pose_estimation.simulation_scan_matching.enabled
        ):
            if not self.pose_estimation.enabled:
                raise ValueError(
                    "To enable Simulation scan matching, first enable Robot > Pose estimation."
                )
            if self.coherent_simulation is not None and not simulation_enabled:
                raise ValueError(
                    "To enable Simulation scan matching, first configure and enable Robot > Coherent simulation."
                )
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.lidar.enabled
            ):
                raise ValueError(
                    "To enable Simulation scan matching, enable Robot > Localization sensors > LiDAR sensor."
                )
        if (
            self.pose_estimation is not None
            and self.pose_estimation.occupancy_map_scan_matching.enabled
        ):
            if self.pose_estimation.simulation_scan_matching.enabled:
                raise ValueError(
                    "Choose one map correction method under Robot > Pose estimation: Observed-map localization or Simulation scan matching. Disable the other method."
                )
            if not self.pose_estimation.enabled:
                raise ValueError(
                    "To enable Observed-map localization, first enable Robot > Pose estimation."
                )
            if self.local_mapping is not None and not self.local_mapping.enabled:
                raise ValueError(
                    "To enable Observed-map localization, first enable Robot > Local occupancy mapping."
                )
            if (
                self.localization_sensors is not None
                and not self.localization_sensors.lidar.enabled
            ):
                raise ValueError(
                    "To enable Observed-map localization, enable Robot > Localization sensors > LiDAR sensor."
                )
        return self


@partial_model
class PartialHardwareConfig(HardwareConfig):
    pass


if __name__ == "__main__":
    import json

    with open("config-schema.json", "w") as f:
        json.dump(HardwareConfig.model_json_schema(), f, indent=2)
