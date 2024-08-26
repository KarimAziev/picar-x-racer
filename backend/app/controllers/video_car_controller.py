import asyncio
import json
import os
import traceback
from datetime import datetime, timedelta
from os import environ, geteuid, getlogin, path
from time import localtime, sleep, strftime, time
from typing import List

import numpy as np
import websockets
from app.config.logging_config import setup_logger
from app.config.paths import (
    MUSIC_DIR,
    PHOTOS_DIR,
    SETTINGS_FILE_PATH,
    SOUNDS_DIR,
    STATIC_FOLDER,
    TEMPLATE_FOLDER,
)
from app.controllers.audio_handler import AudioHandler
from app.util.get_ip_address import get_ip_address
from app.util.os_checks import is_raspberry_pi
from app.util.platform_adapters import Picarx, Vilib, get_battery_voltage, reset_mcu
from websockets import WebSocketServerProtocol
from werkzeug.datastructures import FileStorage

logger = setup_logger(__name__)


class VideoCarController:
    def __init__(self):
        self.is_os_raspberry = is_raspberry_pi()
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
        self.audio_handler = AudioHandler()

        if geteuid() != 0 and self.is_os_raspberry:
            logger.warning(
                "The program needs to be run using sudo, otherwise there may be no sound."
            )
        self.speed = 0
        self.status = "stop"
        self.SOUNDS_DIR = SOUNDS_DIR
        self.MUSIC_DIR = MUSIC_DIR
        self.PHOTOS_DIR = PHOTOS_DIR

        self.music_path = environ.get(
            "MUSIC_PATH",
            os.path.join(
                MUSIC_DIR, "Extreme_Epic_Cinematic_Action_-_StudioKolomna.mp3"
            ),
        )
        self.sound_path = environ.get(
            "SOUND_PATH", os.path.join(SOUNDS_DIR, "directives.wav")
        )

        self.STATIC_FOLDER = STATIC_FOLDER
        self.TEMPLATE_FOLDER = TEMPLATE_FOLDER
        self.is_playing_sound_or_music = None

        # Initialize Vilib camera
        self.camera_thread = None
        self.vilib_img = np.zeros((480, 640, 3), dtype=np.uint8)

        self.start_time = time()

        # Load user settings
        self.settings = self.load_settings()

    def load_settings(self):
        try:
            with open(SETTINGS_FILE_PATH, "r") as settings_file:
                settings = json.load(settings_file)
                return settings
        except FileNotFoundError:
            return {
                "default_sound": None,
                "default_music": "Extreme_Epic_Cinematic_Action_-_StudioKolomna.mp3",
                "default_text": "Hello, I'm your video car!",
            }

    def save_settings(self, new_settings):

        existing_settings = self.load_settings()

        merged_settings = {
            **existing_settings,
            **new_settings,
        }

        with open(SETTINGS_FILE_PATH, "w") as settings_file:
            json.dump(merged_settings, settings_file, indent=2)

        self.settings = merged_settings

    async def handle_message(self, websocket: WebSocketServerProtocol, _):
        async for message in websocket:
            data = json.loads(message)
            logger.info(f"Received: {data}")

            action = data.get("action")
            logger.info(data.get("action", "no action"))

            try:
                if action == "move":
                    payload = data.get("payload", {})
                    direction = payload.get("direction", 0)
                    speed = payload.get("speed", 0)
                    self.move(direction, speed)
                elif action == "setServoDirAngle":
                    self.set_servo_angle(data.get("payload", 0))
                elif action == "stop":
                    self.stop()
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
                elif action == "takePhoto":
                    name = self.take_photo()
                    response = json.dumps({"payload": name, "type": action})
                    await websocket.send(response)
                elif action == "drawFPS":
                    Vilib.draw_fps = not Vilib.draw_fps
                    await websocket.send(
                        json.dumps({"payload": Vilib.draw_fps, "type": "drawFPS"})
                    )
                elif action == "avoidObstacles":
                    now = datetime.utcnow()
                    if self.last_toggle_time and (
                        now - self.last_toggle_time
                    ) < timedelta(seconds=1):
                        logger.info(
                            "Debounce: Too quick toggle of avoidObstacles detected."
                        )
                        continue
                    self.last_toggle_time = now
                    self.avoid_obstacles_mode = not self.avoid_obstacles_mode
                    self.stop()
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
                                logger.info("Avoid obstacles task was cancelled")
                                self.avoid_obstacles_task = None

                elif action == "getDistance":
                    distance = self.get_distance()
                    response = json.dumps({"payload": distance, "type": action})
                    await websocket.send(response)
                elif action == "getBatteryVoltage":
                    value: float = get_battery_voltage()
                    response = json.dumps({"payload": value, "type": action})
                    await websocket.send(response)
                else:
                    error_msg = "Unknown action: {action}"
                    logger.warning(error_msg)
                    response = json.dumps({"error": error_msg, "type": action})
                    await websocket.send(response)
            except Exception as e:
                logger.error(f"Error handling action {action}: {e}")
                logger.error(traceback.format_exc())
                error_response = json.dumps({"type": action, "error": str(e)})
                await websocket.send(error_response)

    def take_photo(self):
        _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
        name = "photo_%s" % _time

        Vilib.take_photo(name, path=self.PHOTOS_DIR)
        return f"{name}.jpg"

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
                distance = round(self.px.ultrasonic.read(), 2)
                logger.info(f"distance: {distance}")
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

    def play_music(self, file=None):
        """
        Handle playing a file based on the given file path.

        Args:
            file: absolute or relative path to a sound file.
        """
        file = file or self.settings.get("default_music") or self.music_path
        if file:
            path_to_file = (
                file if os.path.isabs(file) else os.path.join(self.MUSIC_DIR, file)
            )
            self.audio_handler.play_music(path_to_file)
            logger.info(f"Music finished: {path_to_file}")
        else:
            logger.warning("No music file specified or available to play.")

    def play_sound(self, file=None):
        """
        Handle playing a sound file based on the given file path.

        Args:
            file: absolute or relative path to a sound file.
        """
        file = file or self.settings.get("default_sound") or self.sound_path
        if file:
            path_to_file = (
                file
                if os.path.isabs(file) or file == self.sound_path
                else os.path.join(self.SOUNDS_DIR, file)
            )
            self.audio_handler.play_sound(path_to_file)
            logger.info(f"Playing sound: {path_to_file}")
        else:
            logger.warning("No sound file specified or available to play.")

    def say_text(self, text=None):
        text = text or self.settings.get("default_text", "Hello, I'm your video car!")
        self.audio_handler.text_to_speech(text)

    def move(self, direction: int, speed: int):
        logger.info(f"Moving {direction} with speed {speed}")
        if direction == 1:
            self.px.forward(speed)
        elif direction == -1:
            self.px.backward(speed)

    def set_servo_angle(self, angle):
        logger.info(f"Setting servo angle to {angle} degrees")
        self.px.set_dir_servo_angle(angle)

    def set_cam_tilt_angle(self, angle):
        logger.info(f"Setting camera tilt angle to {angle} degrees")
        self.px.set_cam_tilt_angle(angle)

    def set_cam_pan_angle(self, angle):
        logger.info(f"Setting camera pan angle to {angle} degrees")
        self.px.set_cam_pan_angle(angle)

    def stop(self):
        logger.info("Stopping")
        self.px.stop()

    def get_distance(self):
        try:
            distance = self.px.get_distance()
            if distance == -1:
                raise ValueError("Timeout waiting for echo response")
            elif distance == -2:
                raise ValueError("Failed to detect pulse start or end")
            return distance
        except Exception as e:
            logger.error(f"Failed to get distance: {e}")
            raise

    async def start_server(self):
        async with websockets.serve(self.handle_message, "0.0.0.0", 8765):
            await asyncio.Future()  # Run forever

    def main(self):
        Vilib.camera_start(vflip=False, hflip=False)
        while Vilib.flask_img is None:
            logger.info("waiting for flask img")
            sleep(1)

        logger.info("flask img is ready")
        ip_address = get_ip_address()
        logger.info(
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
            Vilib.camera_close()

    def list_files(self, directory: str) -> List[str]:
        """
        Lists all files in the specified directory.
        """
        if not os.path.exists(directory):
            return []

        files = []
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)):
                files.append(file)
        return files

    def remove_file(self, file: str, directory: str):
        """
        Remove file if in directory.
        """

        full_name = os.path.join(directory, file)

        os.remove(full_name)
        return True

    def save_file(self, file: FileStorage, directory: str) -> str:
        """
        Saves uploaded file to the specified directory.
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = file.filename
        if not isinstance(filename, str):
            raise ValueError("Invalid filename.")
        file_path = os.path.join(directory, filename)
        file.save(file_path)
        return file_path
