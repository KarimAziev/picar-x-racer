import websockets
from app.controllers.camera_controller import CameraController
from app.util.logger import Logger
from websockets.server import WebSocketServerProtocol


class StreamController(Logger):
    def __init__(self, camera_controller: CameraController, **kwargs):
        super().__init__(name=__name__, **kwargs)
        self.camera_controller = camera_controller
        self.server = None

    async def video_stream(self, websocket: WebSocketServerProtocol):
        try:
            await self.camera_controller.generate_video_stream_for_websocket(websocket)
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.error(f"Connection closed error: {e}")
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        finally:
            self.logger.info("Video stream ended")
            if self.camera_controller.active_clients == 0:
                self.camera_controller.camera_close()

    async def start_server(self):
        self.logger.info("Starting camera stream server")
        self.server = await websockets.serve(self.video_stream, "0.0.0.0", 8050)
        await self.server.wait_closed()

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
