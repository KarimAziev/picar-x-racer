"""Configuration for wheel/IMU pose fusion and future pose corrections."""

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated


class SimulationScanMatchingConfig(BaseModel):
    """Development-only scan-to-known-world pose correction settings."""

    enabled: EnabledField = Field(
        default=False,
        title="Simulation scan matching",
        description=(
            "Match simulated LiDAR returns against the configured known world and "
            "publish absolute pose corrections. This is a development aid, not a "
            "replacement for localization against a saved real-world map."
        ),
    )
    max_pose_age_ms: Annotated[int, Field(ge=1, le=5000)] = 200
    search_translation_m: Annotated[float, Field(gt=0, le=2, allow_inf_nan=False)] = (
        0.15
    )
    search_heading_deg: Annotated[float, Field(gt=0, le=45, allow_inf_nan=False)] = 8.0
    coarse_translation_step_m: Annotated[
        float, Field(gt=0, le=1, allow_inf_nan=False)
    ] = 0.05
    coarse_heading_step_deg: Annotated[
        float, Field(gt=0, le=20, allow_inf_nan=False)
    ] = 2.0
    refinement_translation_step_m: Annotated[
        float, Field(gt=0, le=0.5, allow_inf_nan=False)
    ] = 0.01
    refinement_heading_step_deg: Annotated[
        float, Field(gt=0, le=10, allow_inf_nan=False)
    ] = 0.5
    max_scan_points: Annotated[int, Field(ge=8, le=720)] = 48
    min_valid_points: Annotated[int, Field(ge=3, le=720)] = 16
    max_mean_error_m: Annotated[float, Field(gt=0, le=2, allow_inf_nan=False)] = 0.08
    max_residual_m: Annotated[float, Field(gt=0, le=5, allow_inf_nan=False)] = 0.5
    position_stddev_m: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] = 0.03
    heading_stddev_deg: Annotated[float, Field(gt=0, le=30, allow_inf_nan=False)] = 1.5

    @model_validator(mode="after")
    def validate_search_resolution(self) -> "SimulationScanMatchingConfig":
        if self.min_valid_points > self.max_scan_points:
            raise ValueError("minimum valid scan points must not exceed the maximum")
        if self.coarse_translation_step_m > self.search_translation_m:
            raise ValueError("coarse translation step must fit inside the search span")
        if self.coarse_heading_step_deg > self.search_heading_deg:
            raise ValueError("coarse heading step must fit inside the search span")
        if self.refinement_translation_step_m > self.coarse_translation_step_m:
            raise ValueError("translation refinement must not exceed the coarse step")
        if self.refinement_heading_step_deg > self.coarse_heading_step_deg:
            raise ValueError("heading refinement must not exceed the coarse step")
        if self.max_mean_error_m > self.max_residual_m:
            raise ValueError("accepted mean error must not exceed the residual cap")
        return self


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
    simulation_scan_matching: SimulationScanMatchingConfig = Field(
        default_factory=SimulationScanMatchingConfig,
        title="Simulation known-world scan matching",
    )


__all__ = ["PoseEstimationConfig", "SimulationScanMatchingConfig"]
