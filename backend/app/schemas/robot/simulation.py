"""Configuration for the coherent whole-vehicle simulator."""

from typing import Literal

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class SimulationSensorImperfectionsConfig(BaseModel):
    """Optional repeatable sensor errors applied after the ideal plant update."""

    enabled: EnabledField = Field(
        default=False,
        title="Simulate sensor imperfections",
        description=(
            "Apply repeatable encoder, steering, IMU, and LiDAR errors while "
            "keeping the simulator ground truth exact."
        ),
    )
    random_seed: Annotated[
        int,
        Field(
            title="Sensor error random seed",
            description="Reusing a seed reproduces the same sensor-error sequence.",
            ge=0,
            le=2_147_483_647,
        ),
    ] = 7
    encoder_scale_error_percent: Annotated[
        float,
        Field(
            title="Encoder scale error",
            description="Systematic rear-wheel distance error in percent.",
            ge=-20,
            le=20,
            allow_inf_nan=False,
        ),
    ] = 1.0
    encoder_noise_stddev_ticks: Annotated[
        float,
        Field(
            title="Encoder noise",
            description="Per-moving-sample Gaussian encoder noise in ticks.",
            ge=0,
            le=100,
            allow_inf_nan=False,
        ),
    ] = 0.35
    steering_bias_deg: Annotated[
        float,
        Field(
            title="Steering sensor bias",
            description="Constant measured wheel-angle offset in degrees.",
            ge=-10,
            le=10,
            allow_inf_nan=False,
        ),
    ] = 0.75
    steering_noise_stddev_deg: Annotated[
        float,
        Field(
            title="Steering sensor noise",
            description="Gaussian measured wheel-angle noise in degrees.",
            ge=0,
            le=5,
            allow_inf_nan=False,
        ),
    ] = 0.15
    imu_yaw_rate_bias_radps: Annotated[
        float,
        Field(
            title="IMU yaw-rate bias",
            description="Constant simulated gyro Z-axis bias in radians per second.",
            ge=-1,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.01
    imu_yaw_rate_noise_stddev_radps: Annotated[
        float,
        Field(
            title="IMU yaw-rate noise",
            description="Gaussian gyro Z-axis noise in radians per second.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.003
    lidar_range_noise_stddev_m: Annotated[
        float,
        Field(
            title="LiDAR range noise",
            description="Gaussian range noise applied to valid returns in metres.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.015
    lidar_dropout_probability: Annotated[
        float,
        Field(
            title="LiDAR return dropout",
            description="Independent probability that a valid simulated return is lost.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.01


class CoherentSimulationConfig(BaseModel):
    """Deterministic Ackermann vehicle, world, and localization-sensor simulation."""

    enabled: EnabledField = False
    update_frequency_hz: Annotated[
        float,
        Field(
            title="Simulation update frequency",
            description="Fixed-rate Ackermann plant and ideal sensor updates.",
            ge=10,
            le=500,
            allow_inf_nan=False,
        ),
    ] = 100.0
    command_timeout_ms: Annotated[
        int,
        Field(
            title="Simulation command timeout",
            description="Stop when final arbiter commands are no longer fresh.",
            ge=50,
            le=5000,
        ),
    ] = 250
    initial_x_m: Annotated[
        float,
        Field(
            title="Initial X position",
            description="Vehicle starting X coordinate in world metres.",
            allow_inf_nan=False,
        ),
    ] = 0.0
    initial_y_m: Annotated[
        float,
        Field(
            title="Initial Y position",
            description="Vehicle starting Y coordinate in world metres.",
            allow_inf_nan=False,
        ),
    ] = 0.0
    initial_yaw_rad: Annotated[
        float,
        Field(
            title="Initial heading",
            description="Vehicle starting yaw angle in world radians.",
            allow_inf_nan=False,
        ),
    ] = 0.0
    world_scenario: Literal[
        "empty_room", "single_obstacle", "corridor", "apartment"
    ] = Field(
        default="single_obstacle",
        title="Simulation world",
        description="Deterministic line-segment world used by collision and LiDAR.",
    )
    world_width_m: Annotated[
        float,
        Field(
            title="World width",
            description="Inside width of the simulated room.",
            ge=2,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 6.0
    world_height_m: Annotated[
        float,
        Field(
            title="World height",
            description="Inside height of the simulated room.",
            ge=2,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 6.0
    vehicle_radius_m: Annotated[
        float,
        Field(
            title="Vehicle collision radius",
            description="Conservative circular collision envelope around base_link.",
            gt=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.12
    lidar_scan_frequency_hz: Annotated[
        float,
        Field(
            title="Simulated LiDAR scan frequency",
            description="World-aware scan publication rate during coherent simulation.",
            gt=0,
            le=30,
            allow_inf_nan=False,
        ),
    ] = 10.0
    lidar_quality: Annotated[
        int,
        Field(
            title="Simulated LiDAR return quality",
            description="Quality value assigned to deterministic wall and obstacle hits.",
            ge=0,
            le=255,
        ),
    ] = 100
    sensor_imperfections: SimulationSensorImperfectionsConfig = Field(
        default_factory=SimulationSensorImperfectionsConfig,
        title="Simulated sensor imperfections",
        description=(
            "Optional deterministic bias, noise, scale error, and dropout applied "
            "to simulated sensor measurements."
        ),
    )

    @model_validator(mode="after")
    def validate_watchdog_rate(self) -> Self:
        minimum_timeout_ms = 2000 / self.update_frequency_hz
        if self.command_timeout_ms < minimum_timeout_ms:
            raise ValueError(
                "simulation command timeout must cover at least two update cycles"
            )
        if self.lidar_scan_frequency_hz > self.update_frequency_hz:
            raise ValueError(
                "simulated LiDAR frequency must not exceed the plant update frequency"
            )
        half_width = self.world_width_m / 2
        half_height = self.world_height_m / 2
        if self.vehicle_radius_m >= min(half_width, half_height):
            raise ValueError("vehicle collision radius must fit inside the world")
        if abs(self.initial_x_m) > half_width - self.vehicle_radius_m:
            raise ValueError("initial_x_m must place the vehicle inside the world")
        if abs(self.initial_y_m) > half_height - self.vehicle_radius_m:
            raise ValueError("initial_y_m must place the vehicle inside the world")
        return self


__all__ = ["CoherentSimulationConfig", "SimulationSensorImperfectionsConfig"]
