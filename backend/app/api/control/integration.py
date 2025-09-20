"""
Endpoints to synchronize configuration settings from the main application to the robot
application.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.core.px_logger import Logger
from app.schemas.settings import Settings
from app.util.doc_util import build_response_description
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.control.car_service import CarService


router = APIRouter()

_log = Logger(name=__name__)


@router.post(
    "/px/api/settings/update",
    response_model=Settings,
    summary="Synchronize application settings from the main app to dependent "
    "robot services.",
    response_description=build_response_description(
        Settings, "A successful response containing the updated settings."
    ),
)
async def update_settings(
    new_settings: Settings,
    robot_service: Annotated["CarService", Depends(robot_deps.get_robot_service)],
):
    """
    Update application settings for dependent services.

    Typically, when settings changes occur in the main app, this endpoint is invoked by an
    integration service via HTTP to update the internal configuration of robot-dependent services.
    """
    robot_service.app_settings = new_settings

    _log.debug("Updating robot app settings")

    return new_settings
