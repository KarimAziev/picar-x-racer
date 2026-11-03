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
            description="Use the same number to repeat the same sequence of simulated sensor errors.",
            ge=0,
            le=2_147_483_647,
        ),
    ] = 7
    encoder_scale_error_percent: Annotated[
        float,
        Field(
            title="Encoder scale error (%)",
            description="Make the wheels report a consistently wrong distance. 1 means 1% too far; -1 means 1% too short.",
            ge=-20,
            le=20,
            allow_inf_nan=False,
        ),
    ] = 1.0
    encoder_noise_stddev_ticks: Annotated[
        float,
        Field(
            title="Encoder noise",
            description="Amount of random variation added to wheel counts while moving, expressed as a standard deviation. 0 disables this noise.",
            ge=0,
            le=100,
            allow_inf_nan=False,
        ),
    ] = 0.35
    steering_bias_deg: Annotated[
        float,
        Field(
            title="Steering sensor bias (degrees)",
            description="Add this fixed error to every reported steering angle. Positive and negative values bias the reading in opposite directions.",
            ge=-10,
            le=10,
            allow_inf_nan=False,
        ),
    ] = 0.75
    steering_noise_stddev_deg: Annotated[
        float,
        Field(
            title="Steering sensor noise (degrees)",
            description="Random variation in the reported steering angle, expressed as a standard deviation. 0 disables this noise.",
            ge=0,
            le=5,
            allow_inf_nan=False,
        ),
    ] = 0.15
    imu_yaw_rate_bias_radps: Annotated[
        float,
        Field(
            title="IMU yaw-rate bias (rad/s)",
            description="Add this fixed error to the simulated turning-speed reading. It makes the estimated direction drift over time.",
            ge=-1,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.01
    imu_yaw_rate_noise_stddev_radps: Annotated[
        float,
        Field(
            title="IMU yaw-rate noise (rad/s)",
            description="Random variation in the simulated turning-speed reading, expressed as a standard deviation. 0 disables this noise.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.003
    lidar_range_noise_stddev_m: Annotated[
        float,
        Field(
            title="LiDAR range noise (m)",
            description="Random variation in measured obstacle distances, expressed as a standard deviation. 0.015 m means 1.5 cm; 0 disables this noise.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.015
    lidar_dropout_probability: Annotated[
        float,
        Field(
            title="LiDAR return dropout",
            description="Chance of losing each simulated distance reading. 0.01 means 1%; 0 keeps every reading.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.01


class CoherentSimulationConfig(BaseModel):
    """Deterministic Ackermann vehicle, world, and localization-sensor simulation."""

    enabled: EnabledField = Field(
        default=False,
        description="Run driving commands on a virtual robot with physical motors isolated. Configure Motion control and Ackermann odometry, then save all three sections together with the bottom Save button.",
    )
    update_frequency_hz: Annotated[
        float,
        Field(
            title="Simulation update frequency (Hz)",
            description="How often the virtual robot position and wheel readings update each second. Higher rates use more processing.",
            ge=10,
            le=500,
            allow_inf_nan=False,
        ),
    ] = 100.0
    command_timeout_ms: Annotated[
        int,
        Field(
            title="Simulation command timeout (ms)",
            description="Stop the virtual robot if no renewed driving command arrives within this time. 250 ms is a quarter of a second.",
            ge=50,
            le=5000,
        ),
    ] = 250
    initial_x_m: Annotated[
        float,
        Field(
            title="Initial X position (m)",
            description="Starting position along the room X axis. 0 is the room center; positive values move toward positive X. The robot must fit inside the room.",
            allow_inf_nan=False,
        ),
    ] = 0.0
    initial_y_m: Annotated[
        float,
        Field(
            title="Initial Y position (m)",
            description="Starting position along the room Y axis. 0 is the room center; positive values move toward positive Y. The robot must fit inside the room.",
            allow_inf_nan=False,
        ),
    ] = 0.0
    initial_yaw_rad: Annotated[
        float,
        Field(
            title="Initial heading (rad)",
            description="Starting direction: 0 faces positive X; 1.57 radians turns left by about 90 degrees.",
            allow_inf_nan=False,
        ),
    ] = 0.0
    world_scenario: Literal[
        "empty_room", "single_obstacle", "corridor", "apartment"
    ] = Field(
        default="single_obstacle",
        title="Simulation world",
        description="Choose the room and obstacles the virtual robot drives through and detects with LiDAR.",
    )
    world_width_m: Annotated[
        float,
        Field(
            title="World width (m)",
            description="Room size along the X axis. The room extends half this distance on each side of its center.",
            ge=2,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 6.0
    world_height_m: Annotated[
        float,
        Field(
            title="World height (m)",
            description="Room size along the Y axis in the top-down view. This is floor space, not ceiling height.",
            ge=2,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 6.0
    vehicle_radius_m: Annotated[
        float,
        Field(
            title="Vehicle collision radius (m)",
            description="Radius of the circle used to check whether the virtual robot hits an obstacle. Include the whole body. Navigation geometry can override this with measured body dimensions.",
            gt=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.12
    lidar_scan_frequency_hz: Annotated[
        float,
        Field(
            title="Simulated LiDAR scan frequency (Hz)",
            description="How many complete scans of the virtual room are produced each second. Higher rates update the map more often.",
            gt=0,
            le=30,
            allow_inf_nan=False,
        ),
    ] = 10.0
    lidar_quality: Annotated[
        int,
        Field(
            title="Simulated LiDAR return quality",
            description="Signal quality assigned to simulated obstacle readings on a 0–255 scale. Keep the default for normal simulation.",
            ge=0,
            le=255,
        ),
    ] = 100
    sensor_imperfections: SimulationSensorImperfectionsConfig = Field(
        default_factory=SimulationSensorImperfectionsConfig,
        title="Simulated sensor imperfections",
        description=(
            "Add repeatable measurement errors to test how well the position estimate handles imperfect sensors."
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
