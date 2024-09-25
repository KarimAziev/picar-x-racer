from typing import TYPE_CHECKING

from app.deps import get_car_manager
from app.schemas.distance import DistanceData
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.controllers.car_controller import CarController

router = APIRouter()


@router.get("/api/get-distance", response_model=DistanceData)
async def get_ultrasonic_distance(
    car_manager: "CarController" = Depends(get_car_manager),
):
    value: float = await car_manager.px.get_distance()
    return {"distance": value}
