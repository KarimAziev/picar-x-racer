"""Endpoints for non-localization sensor telemetry."""

from typing import TYPE_CHECKING, List

from app.schemas.auxiliary_sensors import AuxiliarySensorReading
from fastapi import APIRouter, Request

if TYPE_CHECKING:
    from app.services.sensors.auxiliary_sensor_service import AuxiliarySensorService


router = APIRouter()


@router.get(
    "/px/api/auxiliary-sensors",
    response_model=List[AuxiliarySensorReading],
    summary="Read all enabled auxiliary sensors.",
)
async def get_auxiliary_sensor_readings(
    request: Request,
) -> List[AuxiliarySensorReading]:
    service: "AuxiliarySensorService" = request.app.state.auxiliary_sensor_service
    return await service.broadcast_state()
