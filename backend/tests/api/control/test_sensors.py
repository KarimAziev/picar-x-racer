import unittest
import json
from pathlib import Path
from typing import cast
from unittest.mock import Mock, AsyncMock

from app.schemas.autonomy import SensorPublisherStatus
from app.services.autonomy import LocalizationSensorService
from app.schemas.robot.config import HardwareConfig
from app.api import robot_deps
from app.api.control.sensors import (
    _close_telemetry_websocket,
    _require_mapping_service,
    get_mapping_session_status,
)
from app.control_server import app as control_app
from app.services.autonomy import (
    LocalMappingService,
    LocalOccupancyGrid,
    LocalOccupancyGridConfig,
    TopicBus,
)
from fastapi import HTTPException, WebSocket
from httpx import ASGITransport, AsyncClient
from starlette.websockets import WebSocketState


class FakeWebSocket:
    def __init__(
        self,
        *,
        application_state: WebSocketState = WebSocketState.CONNECTED,
        client_state: WebSocketState = WebSocketState.CONNECTED,
        close_error: RuntimeError | None = None,
    ) -> None:
        self.application_state = application_state
        self.client_state = client_state
        self.close_error = close_error
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class TelemetryWebSocketCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_does_not_close_after_peer_disconnect(self) -> None:
        websocket = FakeWebSocket()

        await _close_telemetry_websocket(
            cast(WebSocket, websocket), peer_disconnected=True
        )

        self.assertEqual(websocket.close_calls, 0)

    async def test_does_not_close_when_client_state_is_disconnected(self) -> None:
        websocket = FakeWebSocket(client_state=WebSocketState.DISCONNECTED)

        await _close_telemetry_websocket(
            cast(WebSocket, websocket), peer_disconnected=False
        )

        self.assertEqual(websocket.close_calls, 0)

    async def test_closes_connected_socket(self) -> None:
        websocket = FakeWebSocket()

        await _close_telemetry_websocket(
            cast(WebSocket, websocket), peer_disconnected=False
        )

        self.assertEqual(websocket.close_calls, 1)

    async def test_ignores_duplicate_close_race(self) -> None:
        websocket = FakeWebSocket(
            close_error=RuntimeError(
                "Unexpected ASGI message 'websocket.close', after sending "
                "'websocket.close' or response already completed."
            )
        )

        await _close_telemetry_websocket(
            cast(WebSocket, websocket), peer_disconnected=False
        )

        self.assertEqual(websocket.close_calls, 1)

    async def test_propagates_unexpected_close_error(self) -> None:
        websocket = FakeWebSocket(close_error=RuntimeError("socket failure"))

        with self.assertRaisesRegex(RuntimeError, "socket failure"):
            await _close_telemetry_websocket(
                cast(WebSocket, websocket), peer_disconnected=False
            )


class MappingSessionEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_reports_disabled_state_without_a_mapping_service(self) -> None:
        status = await get_mapping_session_status(None)

        self.assertFalse(status.enabled)
        self.assertEqual(status.state.value, "disabled")

    async def test_rejects_actions_when_mapping_is_disabled(self) -> None:
        with self.assertRaises(HTTPException) as context:
            _require_mapping_service(None)

        self.assertEqual(context.exception.status_code, 409)


class LidarRestartRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        data = json.loads(
            (Path(__file__).resolve().parents[4] / "config.json").read_text()
        )
        data["localization_sensors"]["lidar"].update(
            enabled=True, range_min_m=0.05, range_max_m=12
        )
        self.config = HardwareConfig.model_validate(data)
        self.manager = Mock()
        self.manager.load_data.side_effect = lambda: self.config.model_dump(mode="json")
        self.service = Mock(spec=LocalizationSensorService)
        self.service.restart_failed = AsyncMock(
            return_value=SensorPublisherStatus(
                sensor="lidar",
                enabled=True,
                running=True,
            )
        )
        control_app.dependency_overrides[robot_deps.get_config_manager] = (
            lambda: self.manager
        )
        control_app.dependency_overrides[robot_deps.get_localization_sensor_service] = (
            lambda: self.service
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=control_app), base_url="http://testserver"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        control_app.dependency_overrides.clear()

    async def test_restarts_only_lidar_without_saving_settings(self) -> None:
        response = await self.client.post("/px/api/sensors/lidar/restart")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["running"])
        self.service.restart_failed.assert_awaited_once_with("lidar")
        self.manager.save_data.assert_not_called()

    async def test_returns_actionable_conflict_and_connection_failure(self) -> None:
        for error, code in [
            (ValueError("Already running"), 409),
            (OSError("USB unavailable"), 503),
        ]:
            self.service.restart_failed.side_effect = error
            response = await self.client.post("/px/api/sensors/lidar/restart")
            self.assertEqual(response.status_code, code, response.text)
            self.assertEqual(response.json()["detail"], str(error))

    async def test_rejects_disabled_lidar(self) -> None:
        self.config.localization_sensors.lidar.enabled = False
        response = await self.client.post("/px/api/sensors/lidar/restart")
        self.assertEqual(response.status_code, 409)
        self.service.restart_failed.assert_not_awaited()


class MappingSessionRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = LocalMappingService(
            TopicBus(),
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.1,
        )
        control_app.dependency_overrides[robot_deps.get_local_mapping_service] = (
            lambda: self.service
        )
        control_app.dependency_overrides[
            robot_deps.get_navigation_execution_service
        ] = lambda: None
        mission = Mock()
        mission.running = False
        control_app.dependency_overrides[robot_deps.get_navigation_mission_service] = (
            lambda: mission
        )
        # All requests must share the bus event loop, just like the real server.
        self.client = AsyncClient(
            transport=ASGITransport(app=control_app), base_url="http://testserver"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        control_app.dependency_overrides.clear()

    async def test_operates_mapping_session_over_http(self) -> None:
        initial = await self.client.get("/px/api/map/session")
        started = await self.client.post("/px/api/map/session/start")
        paused = await self.client.post("/px/api/map/session/pause")
        finished = await self.client.post("/px/api/map/session/finish")
        reset = await self.client.post("/px/api/map/session/reset")

        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()["state"], "idle")
        self.assertEqual(started.json()["state"], "active")
        self.assertEqual(started.json()["session_id"], 1)
        self.assertEqual(paused.json()["state"], "paused")
        self.assertEqual(finished.json()["state"], "idle")
        self.assertEqual(reset.json()["state"], "idle")

    async def test_rejects_action_when_mapping_is_disabled(self) -> None:
        control_app.dependency_overrides[robot_deps.get_local_mapping_service] = (
            lambda: None
        )

        response = await self.client.post("/px/api/map/session/start")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Local mapping is disabled")

    async def test_rejects_start_while_navigation_is_active(self) -> None:
        navigation = Mock()
        navigation.running = True
        control_app.dependency_overrides[
            robot_deps.get_navigation_execution_service
        ] = lambda: navigation

        response = await self.client.post("/px/api/map/session/start")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Cancel the active navigation action or mission before starting mapping",
        )
        self.assertEqual(self.service.status.state.value, "idle")

    async def test_rejects_start_while_navigation_mission_is_active(self) -> None:
        mission = Mock()
        mission.running = True
        control_app.dependency_overrides[robot_deps.get_navigation_mission_service] = (
            lambda: mission
        )

        response = await self.client.post("/px/api/map/session/start")

        self.assertEqual(response.status_code, 409)
        self.assertIn("mission", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
