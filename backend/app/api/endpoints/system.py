import asyncio
from typing import TYPE_CHECKING

from app.util.logger import Logger
from app.util.shutdown import power_off
from fastapi import APIRouter, HTTPException, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService

logger = Logger(__name__)

router = APIRouter()


@router.get("/api/system/shutdown")
async def shutdown(
    request: Request,
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
        await connection_manager.warning("Powering off the system")
        await asyncio.to_thread(power_off)
    except Exception:
        logger.error("Failed to shutdown system", exc_info=True)
        await connection_manager.error("Failed to shutdown system")
        raise HTTPException(
            status_code=500,
            detail="Failed to shutdown the system due to an internal error.",
        )
