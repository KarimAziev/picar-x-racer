"""Canonical native topics with ROS-compatible names."""

from app.schemas.autonomy import (
    EncoderState,
    ImuData,
    LaserScan,
    LocalizationPose2D,
    OccupancyGrid,
    Odometry2D,
    PoseObservation2D,
    SafetyState,
    SimulationState,
    SteeringState,
)
from app.services.autonomy.messages import ActuatorCommand
from app.services.autonomy.topic_bus import Topic


LIDAR_SCAN = Topic("/lidar/scan", LaserScan)
IMU_DATA = Topic("/imu/data", ImuData)
ENCODER_STATE = Topic("/encoder/state", EncoderState)
STEERING_STATE = Topic("/steering/state", SteeringState)
ODOMETRY = Topic("/odom", Odometry2D)
LOCALIZATION_POSE = Topic("/pose", LocalizationPose2D)
POSE_OBSERVATION = Topic("/localization/observation", PoseObservation2D)
MOTION_COMMANDED = Topic("/motion/commanded", ActuatorCommand)
SIMULATION_STATE = Topic("/simulation/state", SimulationState)
SAFETY_STATE = Topic("/safety/state", SafetyState)
LOCAL_MAP = Topic("/map", OccupancyGrid)


__all__ = [
    "ENCODER_STATE",
    "IMU_DATA",
    "LIDAR_SCAN",
    "LOCAL_MAP",
    "LOCALIZATION_POSE",
    "MOTION_COMMANDED",
    "ODOMETRY",
    "POSE_OBSERVATION",
    "SAFETY_STATE",
    "SIMULATION_STATE",
    "STEERING_STATE",
]
