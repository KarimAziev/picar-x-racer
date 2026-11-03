"""Configuration for wheel/IMU pose fusion and future pose corrections."""

import math

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated


class SimulationScanMatchingConfig(BaseModel):
    """Development-only scan-to-known-world pose correction settings."""

    enabled: EnabledField = Field(
        default=False,
        title="Simulation scan matching",
        description=(
            "Correct position drift by matching simulated LiDAR readings to the virtual room. Requires Coherent simulation and LiDAR. Disable Observed-map localization when using this method."
        ),
    )
    max_pose_age_ms: Annotated[
        int,
        Field(
            title="Position estimate timeout (ms)",
            description=(
                "Skip map alignment if the robot position estimate is older than this limit. 200 ms is one fifth of a second."
            ),
            ge=1,
            le=5000,
        ),
    ] = 200
    search_translation_m: Annotated[
        float,
        Field(
            title="Translation search radius (m)",
            description="How far to try shifting the estimated position in each map direction to align the scan. A larger range can recover larger errors but takes more processing.",
            gt=0,
            le=2,
            allow_inf_nan=False,
        ),
    ] = 0.15
    search_heading_deg: Annotated[
        float,
        Field(
            title="Heading search radius (degrees)",
            description="How far to try turning the estimated direction to align the scan, in either direction. A larger angle takes more processing.",
            gt=0,
            le=45,
            allow_inf_nan=False,
        ),
    ] = 8.0
    coarse_translation_step_m: Annotated[
        float,
        Field(
            title="Coarse translation step (m)",
            description="Distance between trial positions during the first alignment search. Smaller steps check more positions and take longer.",
            gt=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.05
    coarse_heading_step_deg: Annotated[
        float,
        Field(
            title="Coarse heading step (degrees)",
            description="Angle between trial directions during the first alignment search. Smaller steps check more directions and take longer.",
            gt=0,
            le=20,
            allow_inf_nan=False,
        ),
    ] = 2.0
    refinement_translation_step_m: Annotated[
        float,
        Field(
            title="Refinement translation step (m)",
            description="Distance between trial positions when fine-tuning the best match. Keep this at or below the coarse translation step.",
            gt=0,
            le=0.5,
            allow_inf_nan=False,
        ),
    ] = 0.01
    refinement_heading_step_deg: Annotated[
        float,
        Field(
            title="Refinement heading step (degrees)",
            description="Angle between trial directions when fine-tuning the best match. Keep this at or below the coarse heading step.",
            gt=0,
            le=10,
            allow_inf_nan=False,
        ),
    ] = 0.5
    max_scan_points: Annotated[
        int,
        Field(
            title="Maximum scan points",
            description="Limit how many LiDAR points are used for each alignment attempt. More points can improve matching but take longer to process.",
            ge=8,
            le=720,
        ),
    ] = 48
    min_valid_points: Annotated[
        int,
        Field(
            title="Minimum valid scan points",
            description="Reject an alignment if fewer than this many LiDAR points can be compared with the reference map.",
            ge=3,
            le=720,
        ),
    ] = 16
    max_mean_error_m: Annotated[
        float,
        Field(
            title="Maximum mean error (m)",
            description="Reject an alignment if the average distance between the measured obstacles and the reference is above this value. 0.08 m means 8 cm.",
            gt=0,
            le=2,
            allow_inf_nan=False,
        ),
    ] = 0.08
    max_residual_m: Annotated[
        float,
        Field(
            title="Residual cap (m)",
            description=(
                "Limit how much one badly matched LiDAR point affects the alignment score. 0.5 m treats all errors above 50 cm equally."
            ),
            gt=0,
            le=5,
            allow_inf_nan=False,
        ),
    ] = 0.5
    position_stddev_m: Annotated[
        float,
        Field(
            title="Correction position uncertainty (m)",
            description=(
                "Expected position error of an accepted map correction, expressed as a standard deviation. A smaller value makes the position estimate trust that correction more."
            ),
            gt=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.03
    heading_stddev_deg: Annotated[
        float,
        Field(
            title="Correction heading uncertainty (degrees)",
            description=(
                "Expected direction error of an accepted map correction, expressed as a standard deviation. A smaller value makes the estimate trust that correction more."
            ),
            gt=0,
            le=30,
            allow_inf_nan=False,
        ),
    ] = 1.5

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


class OccupancyMapScanMatchingConfig(SimulationScanMatchingConfig):
    """Local pose correction against an observed, paused or finished map."""

    enabled: EnabledField = Field(
        default=False,
        title="Observed-map localization",
        description="Match LiDAR readings to your map to correct the robot position. Pause or finish the mapping session first; corrections wait while you are adding to the map.",
    )
    occupied_threshold: int = Field(
        default=65,
        ge=1,
        le=100,
        title="Occupied-cell threshold",
        description="Treat a map square as an obstacle when its occupancy score reaches this value on the 0–100 scale.",
    )
    min_occupied_cells: int = Field(
        default=16,
        ge=3,
        le=10000,
        title="Minimum occupied cells",
        description="Wait until the map contains this many obstacle squares before trying to use it to correct the robot position.",
    )
    min_overlap_fraction: float = Field(
        default=0.6,
        gt=0,
        le=1,
        allow_inf_nan=False,
        title="Minimum observed overlap",
        description="Fraction of LiDAR points that must land in already observed map areas. 0.6 means at least 60%.",
    )
    ambiguity_distance_m: float = Field(
        default=0.10,
        gt=0,
        le=1,
        allow_inf_nan=False,
        title="Ambiguity probe distance (m)",
        description="Check another position this far away from the best match. Reject the correction if both positions fit almost equally well.",
    )
    ambiguity_heading_deg: float = Field(
        default=3.0,
        gt=0,
        le=20,
        allow_inf_nan=False,
        title="Ambiguity probe angle (degrees)",
        description="Check another direction this far from the best match. Reject the correction if both directions fit almost equally well.",
    )
    ambiguity_margin_m: float = Field(
        default=0.003,
        gt=0,
        le=0.1,
        allow_inf_nan=False,
        title="Minimum alignment score separation (m)",
        description="How much better the best match must be than competing matches. 0.003 m requires a 3 mm improvement in average error.",
    )

    @model_validator(mode="after")
    def bound_search_work(self) -> "OccupancyMapScanMatchingConfig":
        def count(span: float, step: float) -> int:
            ratio = span / step
            if not math.isfinite(ratio) or ratio > 500_000:
                raise ValueError(
                    "Observed-map localization would take too much processing. Reduce Translation search radius or Heading search radius, increase the search steps, or reduce Maximum scan points."
                )
            return 2 * max(1, math.floor(ratio + 1e-9)) + 1

        coarse = count(
            self.search_translation_m, self.coarse_translation_step_m
        ) ** 2 * count(self.search_heading_deg, self.coarse_heading_step_deg)
        fine = count(
            (self.coarse_translation_step_m + self.refinement_translation_step_m) / 2,
            self.refinement_translation_step_m,
        ) ** 2 * count(
            (self.coarse_heading_step_deg + self.refinement_heading_step_deg) / 2,
            self.refinement_heading_step_deg,
        )
        if (coarse + fine + 11) * self.max_scan_points > 500_000:
            raise ValueError(
                "Observed-map localization would take too much processing. Reduce Translation search radius or Heading search radius, increase the search steps, or reduce Maximum scan points."
            )
        return self


class PoseEstimationConfig(BaseModel):
    """Wheel-odometry and IMU fusion with optional absolute pose corrections."""

    enabled: EnabledField = Field(
        default=False,
        description="Combine wheel movement with available rotation-sensor readings to estimate position and direction. Requires Ackermann odometry; map corrections below are optional.",
    )
    imu_yaw_rate_weight: Annotated[
        float,
        Field(
            title="IMU yaw-rate weight",
            description=(
                "How much to trust the rotation sensor when estimating turns. 0 uses only wheel motion; 1 uses only the gyro while its readings are fresh. Keep 0.35 to blend both."
            ),
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.35
    max_imu_age_ms: Annotated[
        int,
        Field(
            title="Rotation reading timeout (ms)",
            description="Ignore rotation sensor readings older than this limit and use wheel motion for turns. 100 ms is one tenth of a second.",
            ge=1,
            le=5000,
        ),
    ] = 100
    max_pose_observation_age_ms: Annotated[
        int,
        Field(
            title="Position correction timeout (ms)",
            description=(
                "Ignore position corrections older than this limit so a delayed update cannot pull the robot back to an old position. 250 ms is a quarter of a second."
            ),
            ge=1,
            le=5000,
        ),
    ] = 250
    initial_position_stddev_m: Annotated[
        float,
        Field(
            title="Initial position uncertainty (m)",
            description="Expected starting-position error in each map direction, expressed as a standard deviation. 0.02 m means 2 cm. Keep the default unless you know the starting position is less precise.",
            ge=0,
            le=10,
            allow_inf_nan=False,
        ),
    ] = 0.02
    initial_heading_stddev_rad: Annotated[
        float,
        Field(
            title="Initial heading uncertainty (rad)",
            description="Expected starting-direction error, expressed as a standard deviation. 0.035 radians is about 2 degrees. Larger values mean less confidence in the starting direction.",
            ge=0,
            le=3.141593,
            allow_inf_nan=False,
        ),
    ] = 0.035
    position_process_noise_m_per_meter: Annotated[
        float,
        Field(
            title="Position process noise (m/m)",
            description="How much position uncertainty grows with distance travelled. 0.02 means 2 cm of standard deviation per metre. Increase this if the wheels slip often.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.02
    heading_process_noise_rad_per_second: Annotated[
        float,
        Field(
            title="Heading process noise (rad/s)",
            description="How much direction uncertainty grows over time. Larger values mean less confidence in the predicted direction; keep the default unless tuning the position estimate.",
            ge=0,
            le=3.141593,
            allow_inf_nan=False,
        ),
    ] = 0.01
    odometry_heading_noise_fraction: Annotated[
        float,
        Field(
            title="Wheel-heading noise fraction",
            description="Expected error as a fraction of a turn calculated from the wheels. 0.05 means 5%. Increase this if wheel-based turns are unreliable.",
            ge=0,
            le=1,
            allow_inf_nan=False,
        ),
    ] = 0.05
    imu_yaw_rate_stddev_radps: Annotated[
        float,
        Field(
            title="IMU yaw-rate standard deviation (rad/s)",
            description="Expected random error in the gyro turning-speed reading. A larger value means less confidence in the gyro; keep the default unless you have measured its noise.",
            ge=0,
            le=3.141593,
            allow_inf_nan=False,
        ),
    ] = 0.03
    simulation_scan_matching: SimulationScanMatchingConfig = Field(
        default_factory=SimulationScanMatchingConfig,
        title="Simulation known-world scan matching",
        description=(
            "Correct the virtual robot position by matching LiDAR readings to the simulated room. Requires Coherent simulation, Pose estimation, and LiDAR to be enabled."
        ),
    )
    occupancy_map_scan_matching: OccupancyMapScanMatchingConfig = Field(
        default_factory=OccupancyMapScanMatchingConfig,
        title="Observed-map localization",
        description="Correct the robot position by matching nearby obstacles to a map you have already built. Pause or finish mapping to use it. Works with a real or virtual robot.",
    )


__all__ = [
    "OccupancyMapScanMatchingConfig",
    "PoseEstimationConfig",
    "SimulationScanMatchingConfig",
]
