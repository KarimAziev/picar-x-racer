import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI, HTTPException, Request

from app.api.endpoints.system import restart_system, shutdown
from app.services.integration.robot_communication_service import (
    RobotCommunicationService,
)


class TestShutdownConfirmation(unittest.IsolatedAsyncioTestCase):
    async def test_requires_successful_valid_response(self) -> None:
        cases = [
            (200, {"success": True}, True),
            (200, {"success": False, "errors": ["motor stop failed"]}, False),
            (200, {"success": True, "errors": ["motor stop failed"]}, False),
            (200, {"success": "true"}, False),
            (200, {}, False),
            (503, {"success": True}, False),
        ]
        for status, payload, accepted in cases:
            with self.subTest(status=status, payload=payload):
                response = httpx.Response(
                    status,
                    json=payload,
                    request=httpx.Request("POST", "http://robot/shutdown"),
                )
                client = AsyncMock()
                client.post.return_value = response
                with patch(
                    "app.services.integration.robot_communication_service.httpx.AsyncClient"
                ) as factory:
                    factory.return_value.__aenter__.return_value = client
                    service = RobotCommunicationService("http://robot")
                    if accepted:
                        await service.shutdown_robot_services()
                    else:
                        with self.assertRaises(Exception):
                            await service.shutdown_robot_services()

    async def test_connection_timeout_propagates(self) -> None:
        with patch(
            "app.services.integration.robot_communication_service.httpx.AsyncClient"
        ) as factory:
            client = AsyncMock()
            client.post.side_effect = httpx.ReadTimeout("motor shutdown timed out")
            factory.return_value.__aenter__.return_value = client
            with self.assertRaises(httpx.ReadTimeout):
                await RobotCommunicationService(
                    "http://robot"
                ).shutdown_robot_services()

    async def test_host_actions_require_robot_confirmation_before_media_cleanup(
        self,
    ) -> None:
        for endpoint, action in ((shutdown, "power_off"), (restart_system, "restart")):
            for failure in (None, RuntimeError("motor stop not confirmed")):
                with self.subTest(action=action, failure=failure):
                    events: list[str] = []

                    async def confirm() -> None:
                        events.append("robot")
                        if failure is not None:
                            raise failure

                    async def media_cleanup() -> None:
                        events.append("media")

                    app = FastAPI()
                    app.state.app_manager = AsyncMock()
                    request = Request({"type": "http", "app": app})
                    robot = MagicMock(
                        shutdown_robot_services=AsyncMock(side_effect=confirm)
                    )
                    music = MagicMock(cleanup=AsyncMock(side_effect=media_cleanup))
                    detection = MagicMock(
                        cancel_detection_watcher=AsyncMock(),
                        stop_detection_process=AsyncMock(),
                    )
                    with patch(f"app.api.endpoints.system.{action}") as host_action:
                        if failure is not None:
                            with self.assertRaises(HTTPException):
                                await endpoint(request, music, detection, robot)
                            host_action.assert_not_called()
                            music.cleanup.assert_not_awaited()
                        else:
                            await endpoint(request, music, detection, robot)
                            host_action.assert_called_once_with()
                            self.assertEqual(events, ["robot", "media"])
