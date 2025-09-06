import asyncio
import struct
import time
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np
from app.core.logger import Logger
from app.exceptions.camera import (
    CameraDeviceError,
    CameraNotFoundError,
    CameraShutdownInProgressError,
)
from app.util.video_utils import encode
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

if TYPE_CHECKING:
    from app.services.camera.camera_service import CameraService

_log = Logger(name=__name__)


class StreamService:
    """
    The `StreamService` class is responsible for streaming video frames to connected clients.
    """

    def __init__(self, camera_service: "CameraService"):
        _log.info("STREAMSERVICE INIT")
        self.camera_service = camera_service
        self.active_clients = 0
        self.loading = False

    def _check_app_cancelled(self, websocket: WebSocket):
        if websocket.app.state.cancelled or self.camera_service.shutting_down:
            _log.warning("Streaming loop breaks due to cancelled app state.")
            return True

    def generate_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Encode video frame for streaming, including an embedded timestamp and FPS.

        Encodes the video frame in the specified format and returns it as a byte array
        with additional metadata. The frame is prefixed by the frame's timestamp and FPS,
        both packed in binary format as double-precision floating-point numbers.

        The structure of the returned byte array is as follows:
            - First 8 bytes: Timestamp (double-precision float) in seconds since the epoch.
            - Next 8 bytes: FPS (double-precision float) representing the current frame rate.
            - Remaining bytes: Encoded video frame in the specified format (e.g., JPEG).

        Returns:
            The encoded video frame as a byte array, prefixed with the timestamp
            and FPS, or None if no frame is available.
        """

        if self.camera_service.shutting_down:
            raise CameraShutdownInProgressError("The camera is is shutting down")
        if self.camera_service.camera_device_error:
            raise CameraDeviceError(self.camera_service.camera_device_error)
        if frame is not None:
            format_quolity_params = {
                ".jpg": cv2.IMWRITE_JPEG_QUALITY,
                ".webp": cv2.IMWRITE_WEBP_QUALITY,
                ".jpeg": cv2.IMWRITE_JPEG_QUALITY,
            }

            quolity_param = format_quolity_params.get(
                self.camera_service.stream_settings.format
            )

            encode_params = (
                [quolity_param, self.camera_service.stream_settings.quality]
                if quolity_param
                else []
            )

            encoded_frame = encode(
                frame, self.camera_service.stream_settings.format, encode_params
            )

            timestamp = self.camera_service.current_frame_timestamp or time.time()
            timestamp_bytes = struct.pack("d", timestamp)

            fps = self.camera_service.actual_fps or 0.0
            fps_bytes = struct.pack("d", fps)

            return timestamp_bytes + fps_bytes + encoded_frame

    async def generate_video_stream_for_websocket(self, websocket: WebSocket) -> None:
        """
        Streams video frames to the connected WebSocket client.
        """
        skip_count = 0
        last_frame = None
        while (
            websocket.application_state == WebSocketState.CONNECTED
            and not self._check_app_cancelled(websocket)
        ):
            try:
                frame = self.camera_service.stream_img
                if last_frame is frame and last_frame is not None:
                    await asyncio.sleep(0.001)
                    continue
                else:
                    last_frame = frame

                encoded_frame = None

                if frame is not None:
                    encoded_frame = await asyncio.to_thread(self.generate_frame, frame)

                if self._check_app_cancelled(websocket):
                    break

                if encoded_frame is not None:
                    skip_count = 0
                    try:
                        if websocket.application_state == WebSocketState.CONNECTED:
                            if self._check_app_cancelled(websocket):
                                break
                            await websocket.send_bytes(encoded_frame)
                        else:
                            _log.info(
                                "WebSocket connection state is no longer connected"
                            )
                            break
                    except CameraShutdownInProgressError as e:
                        _log.warning("Video stream is shuttind down %s", e)
                    except (
                        WebSocketDisconnect,
                        ConnectionResetError,
                        KeyboardInterrupt,
                    ):
                        _log.info("Video stream WebSocket connection lost")
                        break
                else:
                    if skip_count < 2:
                        _log.info("No encoded frame, waiting %s.", skip_count)
                        skip_count += 1
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                _log.info("Streaming loop got CancelledError.")
                raise

    async def disconnect(self, websocket: WebSocket) -> None:
        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                if websocket.app.state.cancelled:
                    await websocket.close(
                        code=1013,
                        reason="Server is shutting down, no new connections allowed.",
                    )
                else:
                    await websocket.close()
            except Exception:
                pass

    async def video_stream(self, websocket: WebSocket) -> None:
        """
        Handles an incoming WebSocket connection for video streaming.

        Args:
            websocket: The WebSocket connection to the client.
        """
        if self._check_app_cancelled(websocket):
            await self.disconnect(websocket)
            return

        self.active_clients += 1

        _log.info("Video Stream %s connection established", self.active_clients)

        try:

            if (
                not self.camera_service.camera_run
                and not self.camera_service.camera_device_error
                and not self.loading
            ):
                self.loading = True
                await asyncio.to_thread(self.camera_service.start_camera)
                self.loading = False

            if not self._check_app_cancelled(websocket):
                await self.generate_video_stream_for_websocket(websocket)
        except (CameraDeviceError, CameraNotFoundError) as e:
            self.loading = False
            await asyncio.to_thread(self.camera_service.stop_camera)
            _log.error("Video Stream got camera error: %s", e)
            await self.camera_service.notify_camera_error(str(e))
        except (
            WebSocketDisconnect,
            CameraShutdownInProgressError,
            KeyboardInterrupt,
        ):
            _log.info("Video Stream disconnected")
        except asyncio.CancelledError:
            _log.info("Video stream cancelled")
        except RuntimeError as e:
            _log.info("Runtime error in video stream: %s", e)
        except Exception:
            _log.error("Unexpected error error occurred in video stream", exc_info=True)
        finally:
            self.active_clients -= 1
            await self.disconnect(websocket)

            _log.info(
                "Video Stream WebSocket connection %s is ended.",
                self.active_clients,
            )

            if (
                self.camera_service.stream_settings.auto_stop_camera_on_disconnect
                and self.active_clients == 0
            ) and not (
                self.camera_service.stream_settings.video_record
                and not self.camera_service.camera_device_error
            ):
                await asyncio.to_thread(self.camera_service.stop_camera)
