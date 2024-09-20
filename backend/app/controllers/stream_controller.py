import asyncio

from app.controllers.camera_controller import CameraController
from app.util.logger import Logger
from quart.wrappers import Websocket


class StreamController:
    """
    The `StreamController` class manages the WebSocket server responsible for streaming video frames
    to connected clients. It handles starting and stopping the server and provides the handler for
    video streaming connections.

    Attributes:
        camera_controller (CameraController): An instance of `CameraController` to manage camera operations.
        server (Optional[websockets.server.Serve]): The WebSocket server instance.
    """

    def __init__(self, camera_controller: CameraController):
        """
        Initializes the `StreamController` instance.

        Args:
            camera_controller (CameraController): An instance of `CameraController` to manage camera operations.
            **kwargs: Additional keyword arguments passed to the base `Logger` class.
        """
        self.logger = Logger(name=__name__)

        self.camera_controller = camera_controller
        self.server = None
        self.active_clients = 0
        self.lock = asyncio.Lock()

    async def generate_video_stream_for_websocket(self, websocket: Websocket):
        """
        Generates a video frame for streaming.

        Retrieves the latest detection results, overlays detection annotations onto the frame,
        applies any video enhancements, encodes the frame in the specified format, and returns
        it as a byte array ready for streaming.

        Returns:
            Optional[bytes]: The encoded video frame as a byte array, or None if no frame is available.
        """

        await self.camera_controller.start_camera_and_wait_for_stream_img()
        skip_count = 0
        try:
            while True:
                encoded_frame = await self.camera_controller.generate_frame()
                if encoded_frame:
                    try:
                        await websocket.send(encoded_frame)
                    except (ConnectionResetError, asyncio.CancelledError):
                        self.logger.info(
                            f"WebSocket connection lost: {websocket.remote_addr}"
                        )
                        break
                else:
                    if skip_count < 1:
                        self.logger.debug("Stream image is None, skipping frame.")
                        skip_count += 1
                await asyncio.sleep(0)
        except Exception as e:
            self.logger.error(f"Error in srteam {e}")

    async def video_stream(self, websocket: Websocket):
        """
        Handles an incoming WebSocket connection for video streaming.

        This method is called for each new WebSocket connection. It initiates the video stream
        to the client by calling `generate_video_stream_for_websocket` on the `CameraController`.
        It manages exceptions that may occur during streaming and ensures proper cleanup when
        the connection is closed.

        Args:
            websocket (WebSocketServerProtocol): The WebSocket connection to the client.

        Exceptions are logged appropriately, and if there are no more active clients after the
        connection is closed, the camera is stopped to conserve resources.
        """
        self.logger.info(f"WebSocket connection established: {websocket.remote_addr}")
        self.active_clients += 1

        try:
            await self.generate_video_stream_for_websocket(websocket)
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        finally:
            self.active_clients -= 1
            self.logger.info(
                f"WebSocket connection closed: {websocket.remote_addr}, Active clients: {self.active_clients}"
            )
            if self.active_clients == 0:
                await self.camera_controller.stop_camera()
