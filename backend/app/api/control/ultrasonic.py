from typing import TYPE_CHECKING

from app.schemas.distance import DistanceData
from app.util.logger import Logger
from fastapi import APIRouter, Request

logger = Logger(name=__name__, app_name="px-control")

ultrasonic_router = APIRouter()

if TYPE_CHECKING:
    from app.services.car_control.car_service import CarService


@ultrasonic_router.get("/px/api/get-distance", response_model=DistanceData)
async def get_ultrasonic_distance(request: Request):
    """
    Retrieve the current ultrasonic distance measurement from the Picar-X vehicle.

    Returns:
        DistanceData: The current distance measurement.
    """
    car_manager: "CarService" = request.app.state
    value: float = await car_manager.px.get_distance()
    return {"distance": value}
