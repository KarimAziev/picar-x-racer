"""Diagnostics for configured localization sensor publishers."""

from typing import Annotated

from app.api import robot_deps
from app.schemas.autonomy import LocalizationSensorStatus
from app.services.autonomy import LocalizationSensorService
from fastapi import APIRouter, Depends


router = APIRouter()


@router.get(
    "/px/api/sensors/status",
    response_model=LocalizationSensorStatus,
    summary="Retrieve LiDAR, IMU, and encoder publisher diagnostics",
)
def get_localization_sensor_status(
    sensor_service: Annotated[
        LocalizationSensorService,
        Depends(robot_deps.get_localization_sensor_service),
    ],
) -> LocalizationSensorStatus:
    return sensor_service.status
