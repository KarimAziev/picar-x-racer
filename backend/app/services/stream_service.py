import asyncio
from typing import TYPE_CHECKING

from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

if TYPE_CHECKING:
    from app.services.camera_service import CameraService


class StreamService(metaclass=SingletonMeta):
    """
    The `StreamService` class is responsible for streaming video frames to connected clients.
    """

    def __init__(self, camera_service: "CameraService"):

        self.logger = Logger(name=__name__)
        self.camera_service = camera_service
        self.active_clients = 0

    async def generate_video_stream_for_websocket(self, websocket: WebSocket) -> None:
        """
        Generates a video frame for streaming.

        Retrieves the latest detection results, overlays detection annotations onto the frame,
        applies any video enhancements, encodes the frame in the specified format, and returns
        it as a byte array ready for streaming.
        """

        skip_count = 0
        while not websocket.app.state.cancelled:
            encoded_frame = await asyncio.to_thread(self.camera_service.generate_frame)
            if encoded_frame:
                skip_count = 0
                try:
                    if websocket.application_state == WebSocketState.CONNECTED:
                        await websocket.send_bytes(encoded_frame)
                    else:
                        self.logger.info(
                            f"WebSocket connection state is no longer connected: {websocket.client}"
                        )
                        break
                except (
                    WebSocketDisconnect,
                    ConnectionResetError,
                ):
                    self.logger.info(f"WebSocket connection lost: {websocket.client}")
                    break

            else:
                if skip_count < 1:
                    self.logger.debug("No encoded frame, waiting.")
                    skip_count += 1

    async def video_stream(self, websocket: WebSocket) -> None:
        """
        Handles an incoming WebSocket connection for video streaming.

        Args:
            websocket: The WebSocket connection to the client.
        """
        self.logger.info(f"WebSocket connection established: {websocket.client}")
        self.active_clients += 1

        try:
            await self.camera_service.start_camera_and_wait_for_stream_img()
            await self.generate_video_stream_for_websocket(websocket)
        except (CameraDeviceError, CameraNotFoundError) as e:
            self.logger.error("Error starting camera %s", e)
            if websocket.application_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass
        except WebSocketDisconnect:
            self.logger.info(f"WebSocket Disconnected {websocket.client}")
        except asyncio.CancelledError:
            self.logger.info("Gracefully shutting down WebSocket stream connection")
        except Exception:
            self.logger.error("An error occurred in video stream", exc_info=True)
        finally:
            self.active_clients -= 1
            if self.active_clients == 0:
                self.logger.info(
                    f"WebSocket connection closed: {websocket.client}, Active clients: {self.active_clients}"
                )
                self.camera_service.stop_camera()
            else:
                self.logger.info(
                    f"WebSocket connection closed: {websocket.client}, Active clients: {self.active_clients}"
                )
