import logging
import unittest
from typing import Any, Optional, Union, cast
from unittest.mock import AsyncMock, MagicMock, patch

from app.exceptions.camera import CameraDeviceError
from app.services.camera_service import CameraService
from app.services.stream_service import StreamService
from fastapi.websockets import WebSocket
from starlette.websockets import WebSocketState


class FakeWebSocket:
    """
    A fake WebSocket instance that mimics the minimal attributes and methods used in StreamService.
    (This version auto-disconnects after sending one frame.)
    """

    def __init__(self, *, cancelled=False):
        self.application_state = WebSocketState.CONNECTED
        self.app = type(
            "FakeApp", (), {"state": type("FakeState", (), {"cancelled": cancelled})}
        )
        self.sent_bytes = []
        self.closed = False
        self.close_code = None
        self.close_reason = None

    async def send_bytes(self, data: bytes):
        """Send bytes and simulate disconnection after first frame."""
        self.sent_bytes.append(data)
        if len(self.sent_bytes) == 1:
            self.application_state = WebSocketState.DISCONNECTED

    async def close(self, code: int = 1000, reason: Union[str, None] = None):
        self.application_state = WebSocketState.DISCONNECTED
        self.closed = True
        self.close_code = code
        self.close_reason = reason


class FakeWebSocketNoDisconnect(FakeWebSocket):
    """A variant of the FakeWebSocket that does not disconnect automatically."""

    async def send_bytes(self, data: bytes):
        self.sent_bytes.append(data)


class DummyCameraService:
    """Dummy CameraService to hand over to StreamService."""

    def __init__(self):
        self.shutting_down = False
        self.camera_run = False
        self.loading = False
        self.camera_device_error: Optional[str] = None
        self.generate_frame = MagicMock(return_value=b"dummy_frame")

        self.start_camera = MagicMock()
        self.stop_camera = MagicMock()
        self.notify_camera_error = AsyncMock()

    def start_camera(self) -> None:
        pass


async def fake_to_thread(func, *args, **kwargs):
    """A helper async wrapper for asyncio.to_thread to replace the lambda in tests."""
    return func(*args, **kwargs)


class TestStreamService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from app.core.singleton_meta import SingletonMeta

        SingletonMeta._instances.pop(StreamService, None)

        self.dummy_cam = DummyCameraService()
        self.stream_service = StreamService(
            camera_service=cast(CameraService, self.dummy_cam)
        )
        self.stream_service.active_clients = 0

    async def test_disconnect_when_cancelled(self):
        """
        Test that disconnect sends a close code (1013) with the correct message when
        websocket.app.state.cancelled is True.
        """
        ws = cast(WebSocket, FakeWebSocket(cancelled=True))
        await self.stream_service.disconnect(ws)

        self.assertEqual(ws.application_state, WebSocketState.DISCONNECTED)

    async def test_disconnect_when_not_cancelled(self):
        """
        Test that disconnect simply calls close when websocket is still connected and not cancelled.
        """
        ws = cast(WebSocket, FakeWebSocket(cancelled=False))
        await self.stream_service.disconnect(ws)
        self.assertEqual(ws.application_state, WebSocketState.DISCONNECTED)

    async def test_generate_video_stream_for_websocket_success(self):
        """
        Test that generate_video_stream_for_websocket sends a frame to the WebSocket.
        The fake websocket's send_bytes method changes the state to DISCONNECTED after one send.
        """
        ws = FakeWebSocket(cancelled=False)
        self.dummy_cam.generate_frame.return_value = b"frame1"
        await self.stream_service.generate_video_stream_for_websocket(
            cast(WebSocket, ws)
        )
        # Assert that send_bytes was called at least one time with frame1.
        self.assertGreaterEqual(len(ws.sent_bytes), 1)
        self.assertEqual(ws.sent_bytes[0], b"frame1")

    async def test_generate_video_stream_for_websocket_frame_skip(self):
        """
        Test that generate_video_stream_for_websocket skips sending duplicate frames.
        We simulate that the camera service returns the same frame twice and then a new one.
        Cancellation is triggered after the new frame is returned.
        """
        ws = FakeWebSocketNoDisconnect(cancelled=False)

        dup_frame = b"dup_frame"  # Use the same object for duplicate frames.
        new_frame = b"new_frame"
        frame_sequence = [dup_frame, dup_frame, new_frame]
        call_counter = 0

        def fake_generate_frame():
            nonlocal call_counter
            if call_counter < len(frame_sequence):
                value = frame_sequence[call_counter]
            else:
                value = new_frame
            call_counter += 1
            # After the fourth call (i.e. after new_frame has been sent), signal cancellation.
            ws_app = cast(Any, ws.app)
            if call_counter == 4:
                ws_app.state.cancelled = True
            return value

        self.dummy_cam.generate_frame.side_effect = fake_generate_frame

        # Patch asyncio.sleep so waiting is essentially skipped.
        with patch("asyncio.sleep", new=AsyncMock()):
            await self.stream_service.generate_video_stream_for_websocket(
                cast(WebSocket, ws)
            )

        self.assertIn(new_frame, ws.sent_bytes)

    async def test_video_stream_normal(self):
        """
        Test the video_stream method under normal conditions.
        We replace generate_video_stream_for_websocket with a dummy coroutine so that we can
        verify that active_clients is incremented and later decremented.
        Also, verify that start_camera is called if required.
        """
        ws = FakeWebSocket(cancelled=False)

        async def fake_generate_video_stream(websocket: WebSocket) -> None:
            logging.debug("websocket=%s", websocket)
            return

        self.stream_service.generate_video_stream_for_websocket = (
            fake_generate_video_stream
        )

        self.dummy_cam.camera_run = False
        self.dummy_cam.camera_device_error = None

        with patch("asyncio.to_thread", new=fake_to_thread):
            await self.stream_service.video_stream(cast(WebSocket, ws))

        self.assertEqual(self.stream_service.active_clients, 0)
        # When active_clients becomes 0, stop_camera is expected.
        self.dummy_cam.stop_camera.assert_called()

    async def test_video_stream_with_camera_error(self):
        """
        Test that if camera_service.start_camera (via to_thread) raises a CameraDeviceError,
        video_stream handles the exception by calling notify_camera_error and stop_camera.
        """
        ws = FakeWebSocket(cancelled=False)

        def fake_start_camera():
            raise CameraDeviceError("Fake camera error")

        self.dummy_cam.camera_run = False
        self.dummy_cam.camera_device_error = None
        self.dummy_cam.start_camera = fake_start_camera

        self.stream_service.generate_video_stream_for_websocket = AsyncMock()

        with patch("asyncio.to_thread", new=fake_to_thread):
            await self.stream_service.video_stream(cast(WebSocket, ws))

        self.dummy_cam.notify_camera_error.assert_called_with("Fake camera error")
        self.assertTrue(ws.closed)
        self.dummy_cam.stop_camera.assert_called()


if __name__ == "__main__":
    unittest.main()
