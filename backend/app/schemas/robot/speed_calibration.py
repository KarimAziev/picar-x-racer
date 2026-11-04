"""Measured motor-power samples used to interpolate requested driving speeds."""

from pydantic import BaseModel, Field


class SpeedCalibrationPoint(BaseModel):
    """One motor setting and the steady speed measured by Guided calibration."""

    power_percent: int = Field(
        ge=1,
        le=100,
        title="Motor power (%)",
        description="Motor command used during this trial. 20% is one fifth of the full command range; it is not a fraction of measured speed.",
    )
    speed_mps: float = Field(
        gt=0,
        allow_inf_nan=False,
        title="Measured speed (m/s)",
        description="Steady travel speed observed at this motor power. The guide calculates it from changing LiDAR distance over time.",
    )


def validate_speed_curve(points: list[SpeedCalibrationPoint]) -> None:
    if points and len(points) < 2:
        raise ValueError("Measure at least two motor-power levels for a speed curve.")
    for previous, current in zip(points, points[1:]):
        if (
            current.power_percent <= previous.power_percent
            or current.speed_mps <= previous.speed_mps
        ):
            raise ValueError(
                "Speed calibration points must increase in both power and speed."
            )
