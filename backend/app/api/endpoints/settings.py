"""
Endpoints to retrieve and update various application settings.
"""

import asyncio
from typing import TYPE_CHECKING, Annotated

from app.api import deps
from app.core.logger import Logger
from app.schemas.settings import Settings, SettingsUpdateRequest
from app.util.doc_util import build_response_description
from fastapi import APIRouter, Depends, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.domain.settings_service import SettingsService
    from app.services.integration.robot_communication_service import (
        RobotCommunicationService,
    )

logger = Logger(__name__)

router = APIRouter()


@router.get(
    "/settings",
    response_model=Settings,
    summary="Retrieve application-wide configuration",
    response_description=build_response_description(
        Settings, "Successful response with current settings."
    ),
)
def get_settings(
    file_service: Annotated["SettingsService", Depends(deps.get_settings_service)]
):
    """
    Retrieve the current application settings.
    """
    return file_service.load_settings()


@router.post(
    "/settings",
    response_model=Settings,
    summary="Update current application settings. Also refresh the settings in the robot app.",
    response_description=build_response_description(
        Settings, "Successful response with an all application-wide settings."
    ),
)
async def update_settings(
    request: Request,
    new_settings: SettingsUpdateRequest,
    file_service: Annotated["SettingsService", Depends(deps.get_settings_service)],
    robot_communication_service: Annotated[
        "RobotCommunicationService", Depends(deps.get_robot_communication_service)
    ],
):
    """
    Update the application settings. Also refresh the settings in the robot app.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    data = new_settings.model_dump(exclude_unset=True)

    logger.info("Updating settings with %s", data)

    new_data = await asyncio.to_thread(file_service.save_settings, data)
    await connection_manager.broadcast_json({"type": "settings", "payload": data})

    await robot_communication_service.refresh_robot_settings(new_data)

    return new_data
