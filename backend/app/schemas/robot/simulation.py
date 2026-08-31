"""Configuration for the coherent whole-vehicle simulator."""

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

    @model_validator(mode="after")
    def validate_watchdog_rate(self) -> Self:
        minimum_timeout_ms = 2000 / self.update_frequency_hz
        if self.command_timeout_ms < minimum_timeout_ms:
            raise ValueError(
                "simulation command timeout must cover at least two update cycles"
            )
        return self


__all__ = ["CoherentSimulationConfig"]
