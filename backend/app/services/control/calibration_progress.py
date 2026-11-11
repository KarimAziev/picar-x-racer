"""Capture the settings that a completed calibration depends on."""

from pydantic import JsonValue

from app.schemas.robot.calibration_progress import CalibrationStep
from app.schemas.robot.config import HardwareConfig

_BODY = (
    "ackermann_odometry.wheelbase_m",
    "navigation.body_length_m",
    "navigation.body_width_m",
    "navigation.rear_overhang_m",
)
_STEERING = (
    "steering_servo",
    "localization_sensors.steering.driver",
    "localization_sensors.steering.center_angle_deg",
)
_WHEEL = (
    "ackermann_odometry.wheel_radius_m",
    "ackermann_odometry.encoder_ticks_per_revolution",
    "ackermann_odometry.gear_ratio",
    "localization_sensors.encoder.sensors",
)
_SPEED = (
    "motion_control.forward_speed_curve",
    "motion_control.reverse_speed_curve",
    "motion_control.max_forward_speed_mps",
    "motion_control.max_reverse_speed_mps",
    "motors",
)
_PATHS: dict[CalibrationStep, tuple[str, ...]] = {
    "body": _BODY,
    "lidar_mount": (
        "localization_sensors.lidar.driver",
        "localization_sensors.lidar.transform",
    ),
    "imu_mount": (
        "localization_sensors.imu.driver",
        "localization_sensors.imu.transform",
    ),
    "steering_center": _STEERING,
    "steering_range": (
        *_STEERING,
        "localization_sensors.steering.calibration_points",
        "localization_sensors.steering.invert_direction",
    ),
    "wheel_distance": _WHEEL,
    "imu_bias": ("localization_sensors.imu", "pose_estimation.imu_yaw_bias_radps"),
    "speed": (*_SPEED, *_WHEEL, *_STEERING, "localization_sensors.lidar.transform"),
    "stopping": (
        *_BODY,
        *_SPEED,
        *_WHEEL,
        "lidar_safety.stop_distance_m",
        "lidar_safety.slow_distance_m",
        "localization_sensors.lidar.transform",
    ),
}


def calibration_snapshot(
    config: HardwareConfig, step: CalibrationStep
) -> dict[str, JsonValue]:
    """Return settings whose changes require reviewing this measurement again."""
    data = config.model_dump(mode="json")
    snapshot: dict[str, JsonValue] = {}
    for path in _PATHS[step]:
        value = data
        for key in path.split("."):
            value = value[key]
        snapshot[path] = value
    return snapshot
