from app.util.platform_adapters import Picarx
import asyncio
import json
import traceback
from datetime import datetime, timedelta
from os import getlogin, path
from time import sleep
from app.util.logger import Logger
import websockets
from app.controllers.audio_controller import AudioController
from app.controllers.camera_controller import CameraController
from app.util.get_ip_address import get_ip_address
from app.util.platform_adapters import get_battery_voltage, reset_mcu
from websockets import WebSocketServerProtocol
from app.controllers.files_controller import FilesController


class CarController(Logger):
    def __init__(
        self,
        camera_manager: CameraController,
        file_manager: FilesController,
        audio_manager: AudioController,
        **kwargs,
    ):
        super().__init__(name="CarController", **kwargs)
        self.camera_manager = camera_manager
        self.audio_manager = audio_manager
        self.file_manager = file_manager
        self.last_toggle_time = None
        self.avoid_obstacles_mode = False
        self.avoid_obstacles_task = None

        self.Picarx = Picarx

        self.reset_mcu = reset_mcu
        self.reset_mcu()
        sleep(0.2)  # Allow the MCU to reset

        self.user = getlogin()
        self.user_home = path.expanduser(f"~{self.user}")

        self.loop = asyncio.get_event_loop()
        self.message_queue = asyncio.Queue()
        self.px = self.Picarx()

    async def handle_message(self, websocket: WebSocketServerProtocol, _):
        self.info("handle_message initted")
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action") if data else None
            payload = data.get("payload") if data else None
            if action and payload:
                self.info(f"{action} payload: {payload}")
            elif action:
                self.info(f"{action}")
            else:
                self.info(f"received invalid message {data}")

            try:
                if action == "move":
                    payload = data.get("payload", {})
                    direction = payload.get("direction", 0)
                    speed = payload.get("speed", 0)
                    self.move(direction, speed)
                elif action == "setServoDirAngle":
                    self.set_servo_angle(data.get("payload", 0))
                elif action == "stop":
                    self.px.stop()
                elif action == "setCamTiltAngle":
                    self.set_cam_tilt_angle(data.get("payload", 0))
                elif action == "setCamPanAngle":
                    self.set_cam_pan_angle(data.get("payload", 0))
                elif action == "playMusic":
                    self.play_music(data.get("payload"))
                elif action == "playSound":
                    self.play_sound(data.get("payload"))
                elif action == "sayText":
                    self.say_text(data.get("payload"))
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
                    self.px.stop()
                    self.set_cam_tilt_angle(0)
                    self.set_cam_pan_angle(0)
                    await websocket.send(
                        json.dumps(
                            {
                                "payload": {
                                    "direction": 0,
                                    "servoAngle": 0,
                                    "camPan": 0,
                                    "camTilt": 0,
                                    "speed": 0,
                                    "maxSpeed": 50,
                                    "avoidObstacles": self.avoid_obstacles_mode,
                                },
                                "type": "update",
                            }
                        )
                    )
                    response = json.dumps(
                        {"payload": self.avoid_obstacles_mode, "type": "avoidObstacles"}
                    )
                    await websocket.send(response)
                    if self.avoid_obstacles_mode:
                        self.avoid_obstacles_task = asyncio.create_task(
                            self.avoid_obstacles()
                        )
                    else:
                        if self.avoid_obstacles_task:
                            try:
                                self.avoid_obstacles_task.cancel()
                                await self.avoid_obstacles_task
                            except asyncio.CancelledError:
                                self.info("Avoid obstacles task was cancelled")
                                self.avoid_obstacles_task = None

                elif action == "getDistance":
                    distance = await self.get_distance()
                    response = json.dumps({"payload": distance, "type": action})
                    await websocket.send(response)
                elif action == "getBatteryVoltage":
                    value: float = get_battery_voltage()
                    response = json.dumps({"payload": value, "type": action})
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

    async def process_messages(self, websocket):
        """Continuously process the message queue and send messages."""
        while True:
            message = await self.message_queue.get()
            await websocket.send(message)
            self.message_queue.task_done()

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

    def set_servo_angle(self, angle):
        self.info(f"Setting servo angle to {angle} degrees")
        self.px.set_dir_servo_angle(angle)

    def set_cam_tilt_angle(self, angle):
        self.info(f"Setting camera tilt angle to {angle} degrees")
        self.px.set_cam_tilt_angle(angle)

    def set_cam_pan_angle(self, angle):
        self.info(f"Setting camera pan angle to {angle} degrees")
        self.px.set_cam_pan_angle(angle)

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
