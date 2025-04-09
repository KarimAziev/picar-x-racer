"""
Operations and endpoints related to system-level actions. These include managing
the operating system, such as shutting down, restarting, or performing other
system-related functions. Use these endpoints with caution as they interact
directly with the underlying OS.
"""

import asyncio
from typing import TYPE_CHECKING, Annotated

from app.api import deps
from app.core.logger import Logger
from app.schemas.common import Message
from app.util.shutdown import power_off, restart
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.detection.detection_service import DetectionService
    from app.services.integration.robot_communication_service import (
        RobotCommunicationService,
    )
    from app.services.media.music_service import MusicService


logger = Logger(__name__)

router = APIRouter()


@router.get(
    "/system/shutdown",
    response_model=Message,
    responses={
        200: {
            "description": "A success message that indicates a successful shutdown initiiation.",
            "content": {
                "application/json": {
                    "example": {"message": "System shutdown initiated successfully."}
                }
            },
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to shutdown the system due to an internal error."
                    }
                }
            },
        },
    },
)
async def shutdown(
    request: Request,
    music_service: Annotated["MusicService", Depends(deps.get_music_service)],
    detection_service: Annotated[
        "DetectionService", Depends(deps.get_detection_service)
    ],
    robot_communication_service: Annotated[
        "RobotCommunicationService", Depends(deps.get_robot_communication_service)
    ],
):
    """
    API endpoint to trigger an immediate system shutdown.

    [!CAUTION]
    --------------
    - This operation will terminate all ongoing processes and disconnect users.
    - The system will shut down immediately unless it encounters an error.

    This endpoint notifies connected clients by broadcasting over WebSocket and
    initiates the power-off process for the host machine.

    When invoked, the server will attempt to shut down using systemd via the D-Bus interface.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    try:
        logger.info("Starting the shutdown process...")
        await connection_manager.warning("Powering off the system")
        await detection_service.cancel_detection_watcher()
        await detection_service.stop_detection_process()
        await music_service.cleanup()
        await robot_communication_service.shutdown_robot_services()
        await asyncio.to_thread(power_off)
        return {"message": "System shutdown initiated successfully."}
    except Exception:
        logger.error("Failed to shutdown system", exc_info=True)
        await connection_manager.error("Failed to shutdown system")
        music_service.start_broadcast_task()
        raise HTTPException(
            status_code=500,
            detail="Failed to shutdown the system due to an internal error.",
        )


@router.get(
    "/system/restart",
    response_model=Message,
    responses={
        200: {
            "description": "A message that indicates a successful restart process.",
            "content": {
                "application/json": {
                    "example": {"message": "System restart initiated successfully."}
                }
            },
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to restart the system."}
                }
            },
        },
    },
)
async def restart_system(
    request: Request,
    music_service: Annotated["MusicService", Depends(deps.get_music_service)],
    detection_service: Annotated[
        "DetectionService", Depends(deps.get_detection_service)
    ],
    robot_communication_service: Annotated[
        "RobotCommunicationService", Depends(deps.get_robot_communication_service)
    ],
):
    """
    API endpoint to trigger an immediate system restart.

    [!CAUTION]
    --------------
    - This operation will terminate all ongoing processes and disconnect users.
    - The system will restart immediately unless it encounters an error.

    This endpoint notifies connected clients by broadcasting over WebSocket and
    initiates the restart process for the host machine.

    When invoked, the server will attempt to restart using systemd via the D-Bus interface.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    try:
        await connection_manager.warning("Restarting the system")
        await music_service.cleanup()
        await detection_service.cancel_detection_watcher()
        await detection_service.stop_detection_process()
        await robot_communication_service.shutdown_robot_services()
        await asyncio.to_thread(restart)
        return {"message": "System restart initiated successfully."}
    except Exception:
        logger.error("Failed to restart system", exc_info=True)
        await connection_manager.error("Failed to restart system")
        music_service.start_broadcast_task()
        raise HTTPException(
            status_code=500,
            detail="Failed to restart the system.",
        )
