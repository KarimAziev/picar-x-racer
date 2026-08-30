import unittest
from typing import cast

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
from fastapi.testclient import TestClient
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


class MappingSessionRouteTests(unittest.TestCase):
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
        self.client = TestClient(control_app)

    def tearDown(self) -> None:
        control_app.dependency_overrides.clear()

    def test_operates_mapping_session_over_http(self) -> None:
        initial = self.client.get("/px/api/map/session")
        started = self.client.post("/px/api/map/session/start")
        paused = self.client.post("/px/api/map/session/pause")
        finished = self.client.post("/px/api/map/session/finish")
        reset = self.client.post("/px/api/map/session/reset")

        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()["state"], "idle")
        self.assertEqual(started.json()["state"], "active")
        self.assertEqual(started.json()["session_id"], 1)
        self.assertEqual(paused.json()["state"], "paused")
        self.assertEqual(finished.json()["state"], "idle")
        self.assertEqual(reset.json()["state"], "idle")

    def test_rejects_action_when_mapping_is_disabled(self) -> None:
        control_app.dependency_overrides[robot_deps.get_local_mapping_service] = (
            lambda: None
        )

        response = self.client.post("/px/api/map/session/start")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Local mapping is disabled")


if __name__ == "__main__":
    unittest.main()
