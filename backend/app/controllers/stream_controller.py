import asyncio
from typing import Optional

import websockets
from app.controllers.camera_controller import CameraController
from app.util.logger import Logger
from websockets.server import WebSocketServerProtocol


class StreamController:
    """
    The `StreamController` class manages the WebSocket server responsible for streaming video frames
    to connected clients. It handles starting and stopping the server and provides the handler for
    video streaming connections.

    Attributes:
        camera_controller (CameraController): An instance of `CameraController` to manage camera operations.
        server (Optional[websockets.server.Serve]): The WebSocket server instance.
    """

    def __init__(self, camera_controller: CameraController, port: Optional[int] = 8050):
        """
        Initializes the `StreamController` instance.

        Args:
            camera_controller (CameraController): An instance of `CameraController` to manage camera operations.
            **kwargs: Additional keyword arguments passed to the base `Logger` class.
        """
        self.logger = Logger(name=__name__)
        self.port = port or 8050

        self.camera_controller = camera_controller
        self.server = None

    async def video_stream(self, websocket: WebSocketServerProtocol):
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

        try:
            await self.camera_controller.generate_video_stream_for_websocket(websocket)
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.info("Connection closed")
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        finally:
            self.logger.info("Video stream ended")
            if self.camera_controller.active_clients == 0:
                self.camera_controller.stop_camera()

    async def start_server(self):
        """
        Starts the WebSocket server to handle video streaming connections.

        The server listens on all network interfaces (`0.0.0.0`) at port `8050` and uses
        the `video_stream` method as the handler for incoming connections. It waits
        indefinitely for the server to close, allowing it to serve clients continuously
        until stopped.

        Raises:
            OSError: If the server fails to start due to issues like the port being already in use.
        """

        self.logger.info(f"Starting camera stream server on the port {self.port}")
        self.server = await websockets.serve(self.video_stream, "0.0.0.0", self.port)
        await self.server.wait_closed()

    async def stop_server(self):
        """
        Stops the WebSocket server gracefully.

        If the server is running, this method initiates a shutdown by closing the server
        and waiting for it to finish processing any ongoing connections.
        """

        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def run_streaming_server(self):
        """
        Starts the video streaming servers.
        """

        server_task = self.start_server()
        await asyncio.gather(server_task)
