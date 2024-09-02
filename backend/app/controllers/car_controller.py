from app.util.platform_adapters import Picarx
import asyncio
import json
import traceback
from datetime import datetime, timedelta
from time import sleep
from app.util.logger import Logger
import websockets
from app.controllers.audio_controller import AudioController
from app.controllers.camera_controller import CameraController
from app.util.get_ip_address import get_ip_address
from app.util.platform_adapters import reset_mcu
from websockets import WebSocketServerProtocol
from app.controllers.files_controller import FilesController


class CarController(Logger):
    def __init__(
        self,
        camera_manager: CameraController,
        file_manager: FilesController,
        audio_manager: AudioController,
        picarx: "Picarx",
        **kwargs,
    ):
        super().__init__(name=__name__, **kwargs)
        reset_mcu()
        sleep(0.2)
        self.camera_manager = camera_manager
        self.audio_manager = audio_manager
        self.file_manager = file_manager
        self.px = picarx

        self.last_toggle_time = None
        self.avoid_obstacles_mode = False
        self.avoid_obstacles_task = None
        self.calibration_mode = False

        self.loop = asyncio.get_event_loop()

    async def handle_message(self, websocket: WebSocketServerProtocol, _):
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action") if data else None
            payload = data.get("payload") if data else None
            if action and payload is not None:
                self.info(f"{action} {payload}")
            elif action:
                self.info(f"{action}")
            else:
                self.info(f"received invalid message {data}")

            try:
                if action == "move":
                    payload = data.get("payload", {"direction": 0, "speed": 0})
                    direction = payload.get("direction", 0)
                    speed = payload.get("speed", 0)
                    self.move(direction, speed)
                elif action == "setServoDirAngle":
                    self.px.set_dir_servo_angle(data.get("payload", 0))
                elif action == "stop":
                    self.px.stop()
                elif action == "setCamTiltAngle":
                    self.px.set_cam_tilt_angle(data.get("payload", 0))
                elif action == "setCamPanAngle":
                    self.px.set_cam_pan_angle(data.get("payload", 0))
                elif action == "avoidObstacles":
                    now = datetime.utcnow()
                    if self.last_toggle_time and (
                        now - self.last_toggle_time
                    ) < timedelta(seconds=1):
                        self.info(
                            "Debounce: Too quick toggle of avoidObstacles detected."
                        )
                        continue
                    self.last_toggle_time = now
                    self.avoid_obstacles_mode = not self.avoid_obstacles_mode
                    await self.handle_avoid_obstacles_mode(websocket)

                elif action == "getDistance":
                    distance = await self.get_distance()
                    response = json.dumps({"payload": distance, "type": action})
                    await websocket.send(response)
                else:
                    error_msg = "Unknown action: {action}"
                    self.warning(error_msg)
                    response = json.dumps({"error": error_msg, "type": action})
                    await websocket.send(response)
            except Exception as e:
                self.error(f"Error handling action {action}: {e}")
                self.error(traceback.format_exc())
                error_response = json.dumps({"type": action, "error": str(e)})
                await websocket.send(error_response)

    async def handle_calibration_message(self, websocket: WebSocketServerProtocol, _):
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action") if data else None
            payload = data.get("payload") if data else None

    async def handle_px_reset(self, websocket: WebSocketServerProtocol):
        self.px.stop()
        self.px.set_cam_tilt_angle(0)
        self.px.set_cam_pan_angle(0)
        self.px.set_dir_servo_angle(0)
        await websocket.send(
            json.dumps(
                {
                    "payload": {
                        "direction": 0,
                        "servoAngle": 0,
                        "camPan": 0,
                        "camTilt": 0,
                        "speed": 0,
                        "maxSpeed": 30,
                    },
                    "type": "update",
                }
            )
        )

    async def handle_avoid_obstacles_mode(self, websocket: WebSocketServerProtocol):
        await self.handle_px_reset(websocket)
        response = json.dumps(
            {"payload": self.avoid_obstacles_mode, "type": "avoidObstacles"}
        )
        await websocket.send(response)
        await self.cancel_avoid_obstales_task()
        if self.avoid_obstacles_mode:
            self.avoid_obstacles_task = asyncio.create_task(self.avoid_obstacles())

    async def cancel_avoid_obstales_task(self):
        if self.avoid_obstacles_task:
            try:
                self.avoid_obstacles_task.cancel()
                await self.avoid_obstacles_task
            except asyncio.CancelledError:
                self.info("Avoid obstacles task was cancelled")
                self.avoid_obstacles_task = None

    async def avoid_obstacles(self):
        POWER = 50
        SafeDistance = 40
        DangerDistance = 20
        try:
            while True:
                value = await self.px.ultrasonic.read()
                distance = round(value, 2)
                self.info(f"distance: {distance}")
                if distance >= SafeDistance:
                    self.px.set_dir_servo_angle(0)
                    self.px.forward(POWER)
                elif distance >= DangerDistance:
                    self.px.set_dir_servo_angle(30)
                    self.px.forward(POWER)
                    await asyncio.sleep(0.1)
                else:
                    self.px.set_dir_servo_angle(-30)
                    self.px.backward(POWER)
                    await asyncio.sleep(0.5)

        finally:
            self.px.forward(0)

    def move(self, direction: int, speed: int):
        self.info(f"Moving {direction} with speed {speed}")
        if direction == 1:
            self.px.forward(speed)
        elif direction == -1:
            self.px.backward(speed)

    async def get_distance(self):
        try:
            distance = await self.px.get_distance()
            if distance == -1:
                raise ValueError("Timeout waiting for echo response")
            elif distance == -2:
                raise ValueError("Failed to detect pulse start or end")
            return distance
        except Exception as e:
            self.error(f"Failed to get distance: {e}")
            raise

    async def start_server(self):
        async with websockets.serve(self.handle_message, "0.0.0.0", 8765):
            await asyncio.Future()  # Run forever

    def main(self):
        ip_address = get_ip_address()
        self.info(
            f"\nTo access the frontend, open your browser and navigate to http://{ip_address}:9000\n"
        )

        server_task = self.loop.create_task(self.start_server())
        try:
            self.loop.run_until_complete(server_task)
        except KeyboardInterrupt:
            server_task.cancel()
            self.loop.run_until_complete(server_task)
            self.loop.close()
        finally:
            if self.camera_manager:
                self.camera_manager.camera_close()
