from typing import Any, Dict

import httpx
from app.core.logger import Logger

logger = Logger(__name__)


class RobotCommunicationService:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def shutdown_robot_services(self) -> None:
        """Notify the robot app to shutdown its services."""
        robot_shutdown_url = f"{self.base_url}/px/api/system/shutdown"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(robot_shutdown_url)
                if response.status_code != 200:
                    logger.error(
                        "Robot shutdown call failed. Status: %s, Response: %s",
                        response.status_code,
                        response.text,
                    )
        except Exception as e:
            logger.error("Error calling robot shutdown endpoint: %s", e)

    async def refresh_robot_settings(self, new_settings: Dict[str, Any]) -> None:
        """Refresh settings in the robot app."""
        robot_refresh_url = f"{self.base_url}/px/api/settings/update"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(robot_refresh_url, json=new_settings)
                if response.status_code != 200:
                    logger.error(
                        "Failed to refresh robot settings. Status code: %s, Response: %s",
                        response.status_code,
                        response.text,
                    )
        except Exception as exc:
            logger.error("Error calling robot app refresh endpoint: %s", exc)
