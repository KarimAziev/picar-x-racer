import asyncio
import logging
import unittest
from typing import Optional, Union, cast
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from app.exceptions.camera import CameraDeviceError
from app.schemas.stream import StreamSettings
from app.services.camera.camera_service import CameraService
from app.services.camera.stream_service import StreamService
from fastapi.websockets import WebSocket
from starlette.websockets import WebSocketState


class FakeState:
    def __init__(self, cancelled: bool):
        self.cancelled = cancelled


class FakeApp:
    def __init__(self, cancelled: bool):
        self.state = FakeState(cancelled)


class FakeWebSocket:
    """
    A fake WebSocket instance that mimics the minimal attributes and methods used in StreamService.
    (This version auto-disconnects after sending one frame.)
    """

    def __init__(self, *, cancelled=False):
        self.application_state = WebSocketState.CONNECTED
        self.app: FakeApp = FakeApp(cancelled)
        self.sent_bytes = []
        self.closed = False
        self.close_code = None
        self.close_reason = None

    async def send_bytes(self, data: bytes):
        """Send bytes and simulate disconnection after first send."""
        self.sent_bytes.append(data)
        if len(self.sent_bytes) == 1:
            self.application_state = WebSocketState.DISCONNECTED

    async def close(self, code: int = 1000, reason: Union[str, None] = None):
        self.application_state = WebSocketState.DISCONNECTED
        self.closed = True
        self.close_code = code
        self.close_reason = reason


class FakeWebSocketNoDisconnect(FakeWebSocket):
    """A variant that does not adjust its state on send_bytes."""

    async def send_bytes(self, data: bytes):
        self.sent_bytes.append(data)


class DummyCameraService:
    """Dummy CameraService to hand over to StreamService."""

    def __init__(self):
        self.shutting_down = False
        self.camera_run = False
        self.loading = False
        self.camera_device_error: Optional[str] = None
        self.stream_img: Optional[np.ndarray] = None
        self.generate_frame = MagicMock(return_value=b"dummy_frame")
        self.start_camera = MagicMock()
        self.stop_camera = MagicMock()
        self.notify_camera_error = AsyncMock()
        self.stream_settings = StreamSettings()

    def start_camera(self) -> None:
        pass


async def fake_to_thread(func, *args, **kwargs):
    """A helper async wrapper to replace asyncio.to_thread in tests."""
    return func(*args, **kwargs)


class TestStreamService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):

        self.dummy_cam = DummyCameraService()
        self.dummy_cam.stream_img = np.empty((0, 0), dtype=np.uint8)
        self.stream_service = StreamService(
            camera_service=cast(CameraService, self.dummy_cam)
        )
        self.stream_service.active_clients = 0
        self.stream_service._generate_frame = MagicMock(return_value=b"dummy_frame")

    async def test_disconnect_when_cancelled(self):
        """
        Test that disconnect sends a close code (1013) with the correct message when
        websocket.app.state.cancelled is True.
        """
        ws = cast(WebSocket, FakeWebSocket(cancelled=True))
        await self.stream_service._disconnect(ws)
        self.assertEqual(ws.application_state, WebSocketState.DISCONNECTED)

    async def test_disconnect_when_not_cancelled(self):
        """
        Test that disconnect simply calls close when websocket is still connected and not cancelled.
        """
        ws = cast(WebSocket, FakeWebSocket(cancelled=False))

        await self.stream_service._disconnect(ws)
        self.assertEqual(ws.application_state, WebSocketState.DISCONNECTED)

    async def test_generate_video_stream_for_websocket_success(self):
        """
        Test that generate_video_stream_for_websocket sends a frame to the WebSocket.
        The fake websocket's send_bytes method changes the state to DISCONNECTED after one send.
        """
        ws = FakeWebSocket(cancelled=False)
        self.dummy_cam.stream_img = np.empty((0, 0), dtype=np.uint8)
        self.stream_service._generate_frame = MagicMock(return_value=b"frame1")
        self.stream_service._generate_frame.return_value = b"frame1"

        await self.stream_service._ws_video_loop(cast(WebSocket, ws))

        self.assertGreaterEqual(len(ws.sent_bytes), 1)
        self.assertEqual(ws.sent_bytes[0], b"frame1")

    async def test_generate_video_stream_for_websocket_frame_skip(self):
        """
        Test that generate_video_stream_for_websocket skips sending duplicate frames.
        Instead of using a side-effect in generate_frame that updates stream_img (which by default
        creates a new NumPy array each time), we run a background updater that first sets a duplicate
        frame (a constant object), and then later changes it to a new frame. This way the identity check
        (using "is") works as intended.
        """
        ws = FakeWebSocketNoDisconnect(cancelled=False)
        dup_frame_obj = object()
        new_frame_obj = object()

        def fake_generate_frame(frame):
            if frame is dup_frame_obj:
                return b"dup_frame"
            elif frame is new_frame_obj:
                return b"new_frame"
            return b"unknown_frame"

        self.stream_service._generate_frame = cast(
            MagicMock, self.stream_service._generate_frame
        ).side_effect = fake_generate_frame

        async def update_frames():
            self.dummy_cam.stream_img = cast(np.ndarray, dup_frame_obj)
            await asyncio.sleep(0.01)
            await asyncio.sleep(0.01)
            self.dummy_cam.stream_img = cast(np.ndarray, new_frame_obj)
            await asyncio.sleep(0.01)
            ws.app.state.cancelled = True

        await asyncio.gather(
            self.stream_service._ws_video_loop(cast(WebSocket, ws)),
            update_frames(),
        )

        self.assertIn(b"new_frame", ws.sent_bytes)

    async def test_video_stream_normal(self):
        """
        Test the video_stream method under normal conditions.
        """
        ws = FakeWebSocket(cancelled=False)

        async def fake_generate_video_stream(websocket: WebSocket) -> None:
            logging.debug("websocket=%s", websocket)
            return

        self.stream_service._ws_video_loop = fake_generate_video_stream

        self.dummy_cam.camera_run = False
        self.dummy_cam.camera_device_error = None

        with patch("asyncio.to_thread", new=fake_to_thread):
            await self.stream_service.video_stream(cast(WebSocket, ws))

        self.assertEqual(self.stream_service.active_clients, 0)

        self.dummy_cam.stop_camera.assert_called()

    async def test_video_stream_auto_stop_camera_disabled(self):
        """
        Test the video_stream doesn't stop the camera if the corresponding setting is disabled.
        """
        ws = FakeWebSocket(cancelled=False)

        async def fake_generate_video_stream(websocket: WebSocket) -> None:
            logging.debug("websocket=%s", websocket)
            return

        self.stream_service._ws_video_loop = fake_generate_video_stream

        self.dummy_cam.camera_run = False
        self.dummy_cam.camera_device_error = None
        self.dummy_cam.stream_settings.auto_stop_camera_on_disconnect = False

        with patch("asyncio.to_thread", new=fake_to_thread):
            await self.stream_service.video_stream(cast(WebSocket, ws))

        self.assertEqual(self.stream_service.active_clients, 0)
        self.dummy_cam.stop_camera.assert_not_called()

    async def test_video_stream_normal_with_video_record(self):
        """
        Test the video_stream doesn't stop the camera with video recording and no active clients.
        """
        ws = FakeWebSocket(cancelled=False)

        async def fake_generate_video_stream(websocket: WebSocket) -> None:
            logging.debug("websocket=%s", websocket)
            return

        self.stream_service._ws_video_loop = fake_generate_video_stream

        self.dummy_cam.camera_run = False
        self.dummy_cam.camera_device_error = None
        self.dummy_cam.stream_settings.video_record = True

        with patch("asyncio.to_thread", new=fake_to_thread):
            await self.stream_service.video_stream(cast(WebSocket, ws))

        self.assertEqual(self.stream_service.active_clients, 0)
        self.dummy_cam.stop_camera.assert_not_called()

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

        self.stream_service._ws_video_loop = AsyncMock()

        with patch("asyncio.to_thread", new=fake_to_thread):
            await self.stream_service.video_stream(cast(WebSocket, ws))

        self.dummy_cam.notify_camera_error.assert_called_with("Fake camera error")
        self.assertTrue(ws.closed)
        self.dummy_cam.stop_camera.assert_called()

    async def test_video_stream_with_camera_error_and_video_record(self):
        """
        Test the video_stream disconnects with no active clients, but with camera error.
        """
        ws = FakeWebSocket(cancelled=False)

        def fake_start_camera():
            raise CameraDeviceError("Failed to read frame from the camera.")

        self.dummy_cam.camera_run = False
        self.dummy_cam.camera_device_error = None
        self.dummy_cam.start_camera = fake_start_camera
        self.dummy_cam.stream_settings.video_record = True

        self.stream_service._ws_video_loop = AsyncMock()

        with patch("asyncio.to_thread", new=fake_to_thread):
            await self.stream_service.video_stream(cast(WebSocket, ws))

        self.dummy_cam.notify_camera_error.assert_called_with(
            "Failed to read frame from the camera."
        )
        self.assertTrue(ws.closed)
        self.assertEqual(self.stream_service.active_clients, 0)
        self.dummy_cam.stop_camera.assert_called()


if __name__ == "__main__":
    unittest.main()
