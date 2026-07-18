"""
Endpoints related to the battery monitoring.
"""

from typing import TYPE_CHECKING

from app.core.px_logger import Logger
from app.schemas.battery import BatteryStatusListResponse
from fastapi import APIRouter, Request

if TYPE_CHECKING:
    from app.services.sensors.battery_service import BatteryService

router = APIRouter()
logger = Logger(name=__name__)


@router.get(
    "/px/api/battery-status",
    response_model=BatteryStatusListResponse,
    summary="Retrieve metrics for all enabled batteries and power supplies.",
    response_description="A list of voltage, optional current, percentage, and error metrics.",
)
async def get_battery_metrics(
    request: Request,
):
    """
    Read and broadcast metrics for every enabled battery configuration.

    Current is null when the underlying adapter does not support current sensing.
    A failure from one adapter is returned on that battery's entry and does not
    prevent successful readings from other adapters.
    """
    battery_manager: "BatteryService" = request.app.state.battery_service
    logger.info("Get battery metrics")
    return await battery_manager.broadcast_state()
