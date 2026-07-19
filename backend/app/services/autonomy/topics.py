"""Canonical native topics with ROS-compatible names."""

from app.schemas.autonomy import (
    EncoderState,
    ImuData,
    LaserScan,
    Odometry2D,
    SafetyState,
    SteeringState,
)
from app.services.autonomy.messages import ActuatorCommand
from app.services.autonomy.topic_bus import Topic


LIDAR_SCAN = Topic("/lidar/scan", LaserScan)
IMU_DATA = Topic("/imu/data", ImuData)
ENCODER_STATE = Topic("/encoder/state", EncoderState)
STEERING_STATE = Topic("/steering/state", SteeringState)
ODOMETRY = Topic("/odom", Odometry2D)
MOTION_COMMANDED = Topic("/motion/commanded", ActuatorCommand)
SAFETY_STATE = Topic("/safety/state", SafetyState)


__all__ = [
    "ENCODER_STATE",
    "IMU_DATA",
    "LIDAR_SCAN",
    "MOTION_COMMANDED",
    "ODOMETRY",
    "SAFETY_STATE",
    "STEERING_STATE",
]
