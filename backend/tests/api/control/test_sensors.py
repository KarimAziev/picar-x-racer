import unittest
from typing import cast

from app.api.control.sensors import _close_telemetry_websocket
from fastapi import WebSocket
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


if __name__ == "__main__":
    unittest.main()
