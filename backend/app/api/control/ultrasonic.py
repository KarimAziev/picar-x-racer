from typing import TYPE_CHECKING

from app.api import robot_deps
from app.schemas.distance import DistanceData
from app.util.logger import Logger
from fastapi import APIRouter, Depends

logger = Logger(name=__name__, app_name="px-control")

ultrasonic_router = APIRouter()

if TYPE_CHECKING:
    from app.services.car_control.car_service import CarService


@ultrasonic_router.get("/px/api/get-distance", response_model=DistanceData)
async def get_ultrasonic_distance(
    car_manager: "CarService" = Depends(robot_deps.get_robot_manager),
):
    """
    Retrieve the current ultrasonic distance measurement from the Picar-X vehicle.

    Returns:
        DistanceData: The current distance measurement.
    """
    value: float = await car_manager.px.get_distance()
    return {"distance": value}
