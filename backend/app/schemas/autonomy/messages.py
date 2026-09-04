"""Framed, monotonic messages for sensors and robot state."""

import math
from typing import Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated, Self


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
PositiveFiniteFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class FrozenMessage(BaseModel):
    model_config = ConfigDict(frozen=True)


class MessageHeader(FrozenMessage):
    """Identity, frame, and process-local monotonic observation time."""

    sequence: Annotated[int, Field(ge=0)]
    frame_id: str
    timestamp_monotonic_ns: Annotated[int, Field(ge=0)]
    source_timestamp_ns: Optional[Annotated[int, Field(ge=0)]] = None

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        frame_id = value.strip()
        if not frame_id:
            raise ValueError("frame_id must not be empty")
        if frame_id.startswith("/"):
            raise ValueError("frame_id must not start with a slash")
        return frame_id


class LaserScan(FrozenMessage):
    """One planar range scan in radians and metres."""

    header: MessageHeader
    angle_min_rad: FiniteFloat
    angle_max_rad: FiniteFloat
    angle_increment_rad: PositiveFiniteFloat
    range_min_m: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    range_max_m: PositiveFiniteFloat
    ranges_m: Tuple[float, ...]
    intensities: Optional[Tuple[FiniteFloat, ...]] = None

    @field_validator("ranges_m")
    @classmethod
    def validate_ranges(cls, values: Tuple[float, ...]) -> Tuple[float, ...]:
        if not values:
            raise ValueError("ranges_m must not be empty")
        for value in values:
            if math.isnan(value) or value < 0:
                raise ValueError("ranges_m values must be non-negative or infinity")
        return values

    @model_validator(mode="after")
    def validate_scan_shape(self) -> Self:
        if self.angle_max_rad < self.angle_min_rad:
            raise ValueError("angle_max_rad must not be less than angle_min_rad")
        if self.range_max_m <= self.range_min_m:
            raise ValueError("range_max_m must be greater than range_min_m")
        if self.intensities is not None and len(self.intensities) != len(self.ranges_m):
            raise ValueError("intensities and ranges_m must have equal lengths")
        return self


class ImuData(FrozenMessage):
    """Minimal planar-navigation IMU observation in ``base_link`` SI units."""

    header: MessageHeader
    angular_velocity_z_radps: FiniteFloat
    acceleration_x_mps2: FiniteFloat
    acceleration_y_mps2: FiniteFloat
    acceleration_z_mps2: FiniteFloat
    yaw_rad: Optional[FiniteFloat] = None
    source_frame_id: Optional[str] = None


class EncoderReading(FrozenMessage):
    """Signed cumulative and incremental state for one rear wheel encoder."""

    ticks: int
    delta_ticks: int


class EncoderState(FrozenMessage):
    """Synchronized readings from one or both rear wheel encoders."""

    header: MessageHeader
    left: Optional[EncoderReading] = None
    right: Optional[EncoderReading] = None

    @model_validator(mode="after")
    def require_at_least_one_wheel(self) -> Self:
        if self.left is None and self.right is None:
            raise ValueError("encoder state requires a left or right reading")
        return self

    @property
    def mean_delta_ticks(self) -> float:
        """Return mean rear-wheel motion, or the available side for one sensor."""

        readings = tuple(
            reading for reading in (self.left, self.right) if reading is not None
        )
        return sum(reading.delta_ticks for reading in readings) / len(readings)


class SteeringState(FrozenMessage):
    """Commanded steering plus optional measured wheel angle."""

    header: MessageHeader
    commanded_angle_rad: FiniteFloat
    measured_angle_rad: Optional[FiniteFloat] = None


class Odometry2D(FrozenMessage):
    """Planar odometry pose and twist, normally odom -> base_link."""

    header: MessageHeader
    child_frame_id: str = "base_link"
    x_m: FiniteFloat
    y_m: FiniteFloat
    yaw_rad: FiniteFloat
    linear_speed_mps: FiniteFloat
    yaw_rate_radps: FiniteFloat

    @field_validator("child_frame_id")
    @classmethod
    def validate_child_frame_id(cls, value: str) -> str:
        frame_id = value.strip()
        if not frame_id or frame_id.startswith("/"):
            raise ValueError("child_frame_id must be non-empty and relative")
        return frame_id


class PoseObservation2D(FrozenMessage):
    """External absolute pose observation for a named estimation frame."""

    header: MessageHeader
    x_m: FiniteFloat
    y_m: FiniteFloat
    yaw_rad: FiniteFloat
    position_variance_m2: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    yaw_variance_rad2: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    source: str

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        source = value.strip()
        if not source:
            raise ValueError("pose observation source must not be empty")
        return source


class LocalizationPose2D(FrozenMessage):
    """Wheel/IMU pose estimate with compact diagonal uncertainty."""

    header: MessageHeader
    child_frame_id: str = "base_link"
    x_m: FiniteFloat
    y_m: FiniteFloat
    yaw_rad: FiniteFloat
    linear_speed_mps: FiniteFloat
    yaw_rate_radps: FiniteFloat
    position_variance_m2: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    yaw_variance_rad2: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    fusion_mode: Literal["wheel", "wheel_imu", "corrected"]
    last_correction_source: Optional[str] = None

    @field_validator("child_frame_id")
    @classmethod
    def validate_localization_child_frame_id(cls, value: str) -> str:
        frame_id = value.strip()
        if not frame_id or frame_id.startswith("/"):
            raise ValueError("child_frame_id must be non-empty and relative")
        return frame_id


class LocalizationRuntimeStatus(FrozenMessage):
    """Lifecycle and input-use counters for native pose fusion."""

    enabled: bool
    running: bool
    published_updates: Annotated[int, Field(ge=0)] = 0
    imu_updates_used: Annotated[int, Field(ge=0)] = 0
    imu_updates_rejected: Annotated[int, Field(ge=0)] = 0
    corrections_applied: Annotated[int, Field(ge=0)] = 0
    corrections_rejected: Annotated[int, Field(ge=0)] = 0
    last_position_innovation_m: Optional[
        Annotated[float, Field(ge=0, allow_inf_nan=False)]
    ] = None
    last_heading_innovation_rad: Optional[
        Annotated[float, Field(ge=0, allow_inf_nan=False)]
    ] = None
    latest_pose: Optional[LocalizationPose2D] = None
    error: Optional[str] = None


class ScanMatchingRuntimeStatus(FrozenMessage):
    """Lifecycle, quality, and rejection counters for scan matching."""

    enabled: bool
    running: bool
    scans_received: Annotated[int, Field(ge=0)] = 0
    matches_published: Annotated[int, Field(ge=0)] = 0
    rejected_missing_pose: Annotated[int, Field(ge=0)] = 0
    rejected_pose_timing: Annotated[int, Field(ge=0)] = 0
    rejected_insufficient_points: Annotated[int, Field(ge=0)] = 0
    rejected_quality: Annotated[int, Field(ge=0)] = 0
    last_mean_error_m: Optional[Annotated[float, Field(ge=0, allow_inf_nan=False)]] = (
        None
    )
    last_prior_mean_error_m: Optional[
        Annotated[float, Field(ge=0, allow_inf_nan=False)]
    ] = None
    last_valid_points: Annotated[int, Field(ge=0)] = 0
    last_candidates_evaluated: Annotated[int, Field(ge=0)] = 0
    latest_observation: Optional[PoseObservation2D] = None
    last_rejection: Optional[str] = None
    error: Optional[str] = None


class SimulationState(FrozenMessage):
    """Ground-truth planar state emitted by the coherent simulator."""

    header: MessageHeader
    x_m: FiniteFloat
    y_m: FiniteFloat
    yaw_rad: FiniteFloat
    linear_speed_mps: FiniteFloat
    steering_angle_rad: FiniteFloat
    yaw_rate_radps: FiniteFloat
    longitudinal_acceleration_mps2: FiniteFloat
    lateral_acceleration_mps2: FiniteFloat
    encoder_ticks: int
    collision: bool = False


class SimulationPose2D(FrozenMessage):
    """One pose expressed in the simulator's world frame."""

    x_m: FiniteFloat
    y_m: FiniteFloat
    yaw_rad: FiniteFloat


class SimulationWorldSegment(FrozenMessage):
    """One immutable obstacle edge in the simulator's world frame."""

    start_x_m: FiniteFloat
    start_y_m: FiniteFloat
    end_x_m: FiniteFloat
    end_y_m: FiniteFloat


class SimulationWorldGeometry(FrozenMessage):
    """Known world geometry exposed for simulation diagnostics."""

    scenario: str
    frame_id: str = "world"
    segments: Tuple[SimulationWorldSegment, ...]

    @field_validator("frame_id")
    @classmethod
    def validate_world_frame_id(cls, value: str) -> str:
        frame_id = value.strip()
        if not frame_id or frame_id.startswith("/"):
            raise ValueError("frame_id must be non-empty and relative")
        return frame_id


class SimulationSensorImperfectionStatus(FrozenMessage):
    """Active seeded sensor-error model exposed for simulator diagnostics."""

    enabled: bool
    random_seed: Annotated[int, Field(ge=0)]
    encoder_scale_error_percent: FiniteFloat
    encoder_noise_stddev_ticks: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    steering_bias_deg: FiniteFloat
    steering_noise_stddev_deg: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    imu_yaw_rate_bias_radps: FiniteFloat
    imu_yaw_rate_noise_stddev_radps: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    lidar_range_noise_stddev_m: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    lidar_dropout_probability: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class SimulationRuntimeStatus(FrozenMessage):
    """Lifecycle and isolation status for coherent simulation mode."""

    enabled: bool
    running: bool
    physical_drive_isolated: bool
    published_updates: Annotated[int, Field(ge=0)] = 0
    lidar_published_updates: Annotated[int, Field(ge=0)] = 0
    world: Optional[SimulationWorldGeometry] = None
    odom_origin_in_world: Optional[SimulationPose2D] = None
    sensor_imperfections: Optional[SimulationSensorImperfectionStatus] = None
    latest_state: Optional[SimulationState] = None
    error: Optional[str] = None


class SafetyState(FrozenMessage):
    """Current directional LiDAR safety decision exposed to operators."""

    header: MessageHeader
    forward_blocked: bool
    reverse_blocked: bool
    max_forward_speed_mps: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    max_reverse_speed_mps: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    nearest_obstacle_m: Optional[Annotated[float, Field(ge=0, allow_inf_nan=False)]] = (
        None
    )
    nearest_rear_obstacle_m: Optional[
        Annotated[float, Field(ge=0, allow_inf_nan=False)]
    ] = None
    considered_points: Annotated[int, Field(ge=0)] = 0
    considered_rear_points: Annotated[int, Field(ge=0)] = 0
    reason: Optional[str] = None


class OccupancyGrid(FrozenMessage):
    """ROS-compatible local occupancy grid in row-major order."""

    header: MessageHeader
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    resolution_m: PositiveFiniteFloat
    origin_x_m: FiniteFloat
    origin_y_m: FiniteFloat
    origin_yaw_rad: FiniteFloat = 0.0
    data: Tuple[Annotated[int, Field(ge=-1, le=100)], ...]

    @model_validator(mode="after")
    def validate_data_size(self) -> Self:
        if len(self.data) != self.width * self.height:
            raise ValueError("occupancy data size must equal width times height")
        return self


__all__ = [
    "EncoderReading",
    "EncoderState",
    "ImuData",
    "LaserScan",
    "LocalizationPose2D",
    "LocalizationRuntimeStatus",
    "ScanMatchingRuntimeStatus",
    "MessageHeader",
    "OccupancyGrid",
    "Odometry2D",
    "PoseObservation2D",
    "SafetyState",
    "SimulationState",
    "SimulationPose2D",
    "SimulationRuntimeStatus",
    "SimulationSensorImperfectionStatus",
    "SimulationWorldGeometry",
    "SimulationWorldSegment",
    "SteeringState",
]
