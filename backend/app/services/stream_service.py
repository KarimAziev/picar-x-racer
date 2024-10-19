import asyncio

from app.services.camera_service import CameraService
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class StreamService(metaclass=SingletonMeta):
    """
    The `StreamService` class is responsible for streaming video frames to connected clients.

    It handles starting and stopping the server and provides the handler for video streaming connections.

    Attributes:
        camera_service (CameraService): An instance of `CameraService` to manage camera operations.
        server (Optional[websockets.server.Serve]): The WebSocket server instance.
    """

    def __init__(self, camera_service: CameraService):
        """
        Initializes the `StreamService` instance.

        Args:
            camera_service (CameraService): An instance of `CameraService` to manage camera operations.
            **kwargs: Additional keyword arguments passed to the base `Logger` class.
        """
        self.logger = Logger(name=__name__)

        self.camera_service = camera_service
        self.server = None
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

        await self.camera_service.start_camera_and_wait_for_stream_img()
        skip_count = 0
        log_count = 0
        try:
            while True:
                encoded_frame = await self.camera_service.generate_frame(log_count < 3)
                if log_count < 3:
                    log_count += 1
                if encoded_frame:
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
                        self.logger.info(
                            f"WebSocket connection lost: {websocket.client}"
                        )
                        break
                else:
                    if skip_count < 1:
                        self.logger.debug("No encoded frame, waiting.")
                        skip_count += 1

                await asyncio.sleep(0)
        except Exception as e:
            self.logger.log_exception("Error in stream", e)

    async def video_stream(self, websocket: WebSocket):
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
            await self.generate_video_stream_for_websocket(websocket)
        except WebSocketDisconnect:
            self.logger.info(f"WebSocket Disconnected {websocket.client}")
        except Exception as e:
            self.logger.log_exception("An error occurred", e)
        finally:
            self.active_clients -= 1
            self.logger.info(
                f"WebSocket connection closed: {websocket.client}, Active clients: {self.active_clients}"
            )
            if self.active_clients == 0:
                self.camera_service.stop_camera()
