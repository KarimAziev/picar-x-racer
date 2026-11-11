"""Persisted settings snapshots for reviewed calibration guides."""

from typing import Annotated, Literal

from pydantic import JsonValue, WithJsonSchema

ManualCalibrationStep = Literal["body", "lidar_mount", "imu_mount"]
CalibrationStep = Literal[
    "body",
    "lidar_mount",
    "imu_mount",
    "wheel_distance",
    "speed",
    "imu_bias",
    "steering_center",
    "steering_range",
    "stopping",
]
SnapshotValue = Annotated[JsonValue, WithJsonSchema({})]
CalibrationProgress = dict[CalibrationStep, dict[str, SnapshotValue]]
