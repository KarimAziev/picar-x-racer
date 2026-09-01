"""Configuration for the coherent whole-vehicle simulator."""

from typing import Literal

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class CoherentSimulationConfig(BaseModel):
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
    initial_x_m: Annotated[float, Field(allow_inf_nan=False)] = 0.0
    initial_y_m: Annotated[float, Field(allow_inf_nan=False)] = 0.0
    initial_yaw_rad: Annotated[float, Field(allow_inf_nan=False)] = 0.0
    world_scenario: Literal["empty_room", "single_obstacle", "corridor"] = Field(
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


__all__ = ["CoherentSimulationConfig"]
