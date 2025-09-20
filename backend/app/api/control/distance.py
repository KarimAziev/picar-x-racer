"""
Endpoints related to distance measurements.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.core.px_logger import Logger
from app.schemas.robot.distance import DistanceData
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.sensors.distance_service import DistanceService

logger = Logger(name=__name__)

router = APIRouter()


@router.get(
    "/px/api/get-distance",
    response_model=DistanceData,
    summary="Retrieve the last measured distance",
)
async def get_ultrasonic_distance(
    distance_service: Annotated[
        "DistanceService", Depends(robot_deps.get_distance_service)
    ],
):
    """
    Retrieve the last measured level of the distance.
    """
    value: float = distance_service.distance
    logger.debug("Ultrasonic distance %s", value)
    return {"distance": value}
