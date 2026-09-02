"""Configuration for wheel/IMU pose fusion and future pose corrections."""

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class PoseEstimationConfig(BaseModel):
    enabled: EnabledField = False
    imu_yaw_rate_weight: Annotated[
        float,
        Field(
            title="IMU yaw-rate weight",
            description=(
                "Blend weight for fresh gyro yaw rate; zero keeps wheel odometry "
                "heading and one uses only the gyro increment."
            ),
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.35
    max_imu_age_ms: Annotated[
        int,
        Field(
            title="Maximum IMU age",
            description="Ignore gyro observations older than this odometry sample age.",
            ge=1,
            le=5000,
        ),
    ] = 100
    max_pose_observation_age_ms: Annotated[
        int,
        Field(
            title="Maximum pose-correction age",
            description=(
                "Reject delayed external pose observations until estimator history "
                "and replay are implemented."
            ),
            ge=1,
            le=5000,
        ),
    ] = 250
    initial_position_stddev_m: Annotated[
        float,
        Field(ge=0, le=10, allow_inf_nan=False),
    ] = 0.02
    initial_heading_stddev_rad: Annotated[
        float,
        Field(ge=0, le=3.141593, allow_inf_nan=False),
    ] = 0.035
    position_process_noise_m_per_meter: Annotated[
        float,
        Field(
            title="Position process noise",
            description="Position standard deviation accumulated per metre travelled.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.02
    heading_process_noise_rad_per_second: Annotated[
        float,
        Field(
            title="Heading process noise",
            description="Unmodelled heading-rate standard deviation.",
            ge=0,
            le=3.141593,
            allow_inf_nan=False,
        ),
    ] = 0.01
    odometry_heading_noise_fraction: Annotated[
        float,
        Field(
            title="Wheel-heading noise fraction",
            description="Uncertainty proportional to the wheel-derived yaw increment.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.05
    imu_yaw_rate_stddev_radps: Annotated[
        float,
        Field(
            title="IMU yaw-rate standard deviation",
            description="Expected short-term gyro yaw-rate noise.",
            ge=0,
            le=3.141593,
            allow_inf_nan=False,
        ),
    ] = 0.03


__all__ = ["PoseEstimationConfig"]
