import asyncio
from typing import TYPE_CHECKING

from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.connection_service import ConnectionService


class StreamService(metaclass=SingletonMeta):
    """
    The `StreamService` class is responsible for streaming video frames to connected clients.

    It handles starting and stopping the server and provides the handler for video streaming connections.

    Attributes:
        camera_service (CameraService): An instance of `CameraService` to manage camera operations.
    """

    def __init__(self, camera_service: "CameraService"):
        """
        Initializes the `StreamService` instance.

        Args:
            camera_service (CameraService): An instance of `CameraService` to manage camera operations.
        """
        self.logger = Logger(name=__name__)

        self.camera_service = camera_service
        self.active_clients = 0

    async def generate_video_stream_for_websocket(self, websocket: WebSocket):
        """
        Generates a video frame for streaming.

        Retrieves the latest detection results, overlays detection annotations onto the frame,
        applies any video enhancements, encodes the frame in the specified format, and returns
        it as a byte array ready for streaming.

        Returns:
            Optional[bytes]: The encoded video frame as a byte array, or None if no frame is available.
        """

        skip_count = 0
        while True:
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

            await asyncio.sleep(0)

    async def video_stream(
        self, websocket: WebSocket, connection_service: "ConnectionService"
    ):
        """
        Handles an incoming WebSocket connection for video streaming.

        This method is called for each new WebSocket connection. It initiates the video stream
        to the client by calling `generate_video_stream_for_websocket` on the `CameraService`.
        It manages exceptions that may occur during streaming and ensures proper cleanup when
        the connection is closed.

        Args:
            websocket (WebSocketServerProtocol): The WebSocket connection to the client.

        Exceptions are logged appropriately, and if there are no more active clients after the
        connection is closed, the camera is stopped to conserve resources.
        """
        self.logger.info(f"WebSocket connection established: {websocket.client}")
        self.active_clients += 1

        try:
            await self.camera_service.start_camera_and_wait_for_stream_img()
            await self.generate_video_stream_for_websocket(websocket)
        except (CameraDeviceError, CameraNotFoundError) as e:
            self.logger.error("Error starting camera %s", e)
            await connection_service.error(str(e))

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
