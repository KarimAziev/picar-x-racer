"""
Endpoints related to ultrasonic measurements.
"""

from typing import TYPE_CHECKING

from app.api import robot_deps
from app.schemas.distance import DistanceData
from app.util.logger import Logger
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.distance_service import DistanceService

logger = Logger(name=__name__)

router = APIRouter()


@router.get("/px/api/get-distance", response_model=DistanceData)
async def get_ultrasonic_distance(
    distance_service: "DistanceService" = Depends(robot_deps.get_distance_service),
):
    """
    Retrieve the current ultrasonic distance measurement from the Picar-X vehicle.

    Returns:
        DistanceData: The current distance measurement.
    """
    value: float = distance_service.distance
    return {"distance": value}
