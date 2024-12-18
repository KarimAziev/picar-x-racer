import asyncio
from typing import TYPE_CHECKING

from app.api import deps
from app.util.logger import Logger
from app.util.shutdown import power_off, restart
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.battery_service import BatteryService
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.music_service import MusicService


logger = Logger(__name__)

router = APIRouter()


@router.get("/api/system/shutdown")
async def shutdown(
    request: Request,
    music_manager: "MusicService" = Depends(deps.get_music_manager),
    battery_manager: "BatteryService" = Depends(deps.get_battery_manager),
    detection_manager: "DetectionService" = Depends(deps.get_detection_manager),
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

    Raises:
    --------------
    HTTPException: If the shutdown process fails (e.g., failure to access D-Bus).
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    try:
        logger.info("Starting the shutdown process...")
        await connection_manager.warning("Powering off the system")
        await battery_manager.cleanup_connection_manager()
        await detection_manager.cancel_detection_process_task()
        await detection_manager.stop_detection_process()
        await music_manager.cleanup()
        await asyncio.to_thread(power_off)
        return {"message": "System shutdown initiated successfully."}
    except Exception:
        logger.error("Failed to shutdown system", exc_info=True)
        await connection_manager.error("Failed to shutdown system")
        battery_manager.setup_connection_manager()
        music_manager.start_broadcast_task()
        raise HTTPException(
            status_code=500,
            detail="Failed to shutdown the system due to an internal error.",
        )


@router.get("/api/system/restart")
async def restart_system(
    request: Request,
    music_manager: "MusicService" = Depends(deps.get_music_manager),
    battery_manager: "BatteryService" = Depends(deps.get_battery_manager),
    detection_manager: "DetectionService" = Depends(deps.get_detection_manager),
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

    Raises:
    --------------
    HTTPException: If the restart process fails (e.g., failure to access D-Bus).
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    try:
        await connection_manager.warning("Restarting the system")
        await battery_manager.cleanup_connection_manager()
        await music_manager.cleanup()
        await detection_manager.cancel_detection_process_task()
        await detection_manager.stop_detection_process()
        await asyncio.to_thread(restart)
        return {"message": "System restart initiated successfully."}
    except Exception:
        logger.error("Failed to restart system", exc_info=True)
        await connection_manager.error("Failed to restart system")
        battery_manager.setup_connection_manager()
        music_manager.start_broadcast_task()
        raise HTTPException(
            status_code=500,
            detail="Failed to restart the system.",
        )
