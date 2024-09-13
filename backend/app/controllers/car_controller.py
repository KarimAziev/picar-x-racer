import asyncio
import json
import time
import traceback
from datetime import datetime, timedelta

import websockets
from app.controllers.audio_controller import AudioController
from app.controllers.calibration_controller import CalibrationController
from app.controllers.camera_controller import CameraController
from app.controllers.files_controller import FilesController
from app.controllers.stream_controller import StreamController
from app.util.get_ip_address import get_ip_address
from app.util.logger import Logger
from app.util.platform_adapters import Picarx, reset_mcu
from websockets import WebSocketServerProtocol


class CarController(Logger):
    DEBOUNCE_INTERVAL = timedelta(seconds=1)

    def __init__(
        self,
        camera_manager: CameraController,
        file_manager: FilesController,
        audio_manager: AudioController,
        **kwargs,
    ):
        super().__init__(name=__name__, **kwargs)
        self.camera_manager = camera_manager
        self.audio_manager = audio_manager
        self.file_manager = file_manager

        self.stream_controller = StreamController(camera_controller=self.camera_manager)

        reset_mcu()
        time.sleep(0.2)

        self.px = Picarx()
        self.calibration = CalibrationController(self.px)
        self.last_toggle_time = None
        self.avoid_obstacles_mode = False
        self.is_moving = False
        self.move_track_task = None
        self.avoid_obstacles_task = None

        self.loop = asyncio.get_event_loop()

    async def handle_message(self, websocket: WebSocketServerProtocol, _):
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get("action")
                payload = data.get("payload")
                if action:
                    await self.process_action(action, payload, websocket)
                else:
                    self.info(f"received invalid message {data}")

            except KeyboardInterrupt as e:
                self.error(f"KeyboardInterrupt")
            except Exception as e:
                self.error(f"Error handling message: {message}: {e}")
                self.error(traceback.format_exc())
                error_response = json.dumps({"error": str(e)})
                await websocket.send(error_response)

    async def process_action(self, action: str, payload, websocket):
        self.info(f"Action: '{action}' with payload {payload}")
        calibration_actions_map = {
            "increaseCamPanCali": self.calibration.increase_cam_pan_angle,
            "decreaseCamPanCali": self.calibration.decrease_cam_pan_angle,
            "increaseCamTiltCali": self.calibration.increase_cam_tilt_angle,
            "decreaseCamTiltCali": self.calibration.decrease_cam_tilt_angle,
            "increaseServoDirCali": self.calibration.increase_servo_dir_angle,
            "decreaseServoDirCali": self.calibration.decrease_servo_dir_angle,
            "resetCalibration": self.calibration.servos_reset,
            "saveCalibration": self.calibration.save_calibration,
            "servoTest": self.calibration.servos_test,
        }

        calibrationData = None
        if action in calibration_actions_map:
            calibrationData = calibration_actions_map[action]()
            self.camera_manager.inhibit_detection = True
            if calibrationData:
                await websocket.send(
                    json.dumps(
                        {
                            "type": (
                                "saveCalibration"
                                if action == "saveCalibration"
                                else "updateCalibration"
                            ),
                            "payload": calibrationData,
                        }
                    )
                )
        elif action == "move":
            self.handle_move(payload)
        elif action == "setServoDirAngle":
            self.px.set_dir_servo_angle(payload or 0)
        elif action == "stop":
            self.px.stop()
            self.camera_manager.inhibit_detection = False
        elif action == "setCamTiltAngle":
            self.px.set_cam_tilt_angle(payload)
        elif action == "setCamPanAngle":
            self.px.set_cam_pan_angle(payload)
        elif action == "avoidObstacles":
            await self.toggle_avoid_obstacles_mode(websocket)
        elif action == "getDistance":
            await self.respond_with_distance(action, websocket)
        else:
            error_msg = f"Unknown action: {action}"
            self.warning(error_msg)
            await websocket.send(json.dumps({"error": error_msg, "type": action}))

    def handle_move(self, payload):
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
        self.camera_manager.inhibit_detection = speed != 0

        self.move(direction, speed)

    async def toggle_avoid_obstacles_mode(self, websocket):
        now = datetime.utcnow()
        if (
            self.last_toggle_time
            and (now - self.last_toggle_time) < self.DEBOUNCE_INTERVAL
        ):
            self.info("Debounce: Too quick toggle of avoidObstacles detected.")
            return
        await self.cancel_avoid_obstacles_task()
        await self.handle_px_reset(websocket)
        self.last_toggle_time = now
        self.avoid_obstacles_mode = not self.avoid_obstacles_mode

        response = json.dumps(
            {"payload": self.avoid_obstacles_mode, "type": "avoidObstacles"}
        )
        await websocket.send(response)

        if self.avoid_obstacles_mode:
            self.avoid_obstacles_task = asyncio.create_task(self.avoid_obstacles())

    async def respond_with_distance(self, action, websocket):
        try:
            distance = await self.get_distance()
            response = json.dumps({"payload": distance, "type": action})
            await websocket.send(response)
        except Exception as e:
            error_response = json.dumps({"type": action, "error": str(e)})
            await websocket.send(error_response)

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

    async def cancel_avoid_obstacles_task(self):
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
        errors = {
            -1: "Timeout waiting for echo response",
            -2: "Failed to detect pulse start or end",
        }
        try:
            distance = await self.px.get_distance()
            if distance < 0 and distance in errors:
                raise ValueError(errors.get(distance, "Unexpected distance error"))
            return distance
        except Exception as e:
            self.error(f"Failed to get distance: {e}")
            raise

    async def start_server(self):
        ip_address = get_ip_address()
        self.server = await websockets.serve(self.handle_message, "0.0.0.0", 8765)
        self.info(
            f"\nTo access the frontend, open your browser and navigate to http://{ip_address}:9000\n"
        )
        await self.server.wait_closed()

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    def run_server(self):
        return asyncio.run(self.start_server())

    async def run_streaming_servers(self):
        server_task1 = self.stream_controller.start_server()
        await asyncio.gather(server_task1)
