import asyncio
import json
import os
import socket
from os import environ, geteuid, getlogin, path
from time import localtime, sleep, strftime, time

import numpy as np
import websockets
from util.os_checks import is_raspberry_pi
from util.platform_adapters import Picarx, Vilib, reset_mcu
from websockets import WebSocketServerProtocol

from controllers.audio_handler import AudioHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MUSIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "../music"))
SOUNDS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../sounds"))
SETTINGS_FILE_PATH = os.path.abspath(os.path.join(BASE_DIR, "../user_settings.json"))
STATIC_FOLDER = os.path.join(BASE_DIR, "../front-end/dist/assets")
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "../front-end/dist")
UPLOAD_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "../uploads/"))


class VideoCarController:
    def __init__(self):
        self.is_os_raspberry = is_raspberry_pi()

        self.Picarx = Picarx
        self.reset_mcu = reset_mcu
        self.reset_mcu()
        sleep(0.2)  # Allow the MCU to reset

        self.user = getlogin()
        self.user_home = path.expanduser(f"~{self.user}")

        self.px = self.Picarx()
        self.audio_handler = AudioHandler()

        if geteuid() != 0 and self.is_os_raspberry:
            print(
                f"\033[0;33m{'The program needs to be run using sudo, otherwise there may be no sound.'}\033[0m"
            )
        self.speed = 0
        self.status = "stop"
        self.SOUNDS_DIR = SOUNDS_DIR
        self.MUSIC_DIR = MUSIC_DIR

        self.music_path = environ.get(
            "MUSIC_PATH", os.path.join(MUSIC_DIR, "robomusic.mp3")
        )
        self.sound_path = environ.get(
            "SOUND_PATH", os.path.join(SOUNDS_DIR, "directives.wav")
        )

        self.STATIC_FOLDER = STATIC_FOLDER
        self.TEMPLATE_FOLDER = TEMPLATE_FOLDER
        self.UPLOAD_FOLDER = UPLOAD_FOLDER

        # Initialize Vilib camera
        self.camera_thread = None
        self.vilib_img = np.zeros((480, 640, 3), dtype=np.uint8)

        # Drawing FPS on the image
        self.draw_fps = True
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
                "default_music": None,
                "default_text": "Hello, I'm your video car!",
            }

    def save_settings(self, new_settings):
        with open(SETTINGS_FILE_PATH, "w") as settings_file:
            json.dump(new_settings, settings_file, indent=2)
        self.settings = new_settings

    async def handle_message(self, websocket: WebSocketServerProtocol, _):
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

            action = data.get("action")
            print(data.get("action", "no action"))
            if action == "move":
                self.move(data.get("direction"), data.get("speed", 0))
            elif action == "setServo":
                self.set_servo_angle(data.get("angle", 0))
            elif action == "stop":
                self.stop()
            elif action == "setCamTiltAngle":
                self.set_cam_tilt_angle(data.get("angle", 0))
            elif action == "setCamPanAngle":
                self.set_cam_pan_angle(data.get("angle", 0))
            elif action == "playMusic":
                self.play_music(data.get("file"))
            elif action == "playSound":
                self.play_sound(data.get("file"))
            elif action == "sayText":
                self.say_text(data.get("text"))
            elif action == "takePhoto":
                self.take_photo()

    def take_photo(self):
        _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
        name = "photo_%s" % _time
        photo_path = f"{self.user_home}/Pictures/picar-x/"
        Vilib.take_photo(name, photo_path)
        print("\nphoto saved as %s%s.jpg" % (photo_path, name))

    def play_music(self, file=None):
        """
        Handle playing a file based on the given file path.

        Args:
            file: absolute or relative path to a sound file.
        """
        file = file or self.settings.get("default_music") or self.music_path
        if file:
            path_to_file = (
                file
                if os.path.isabs(file) or file == self.music_path
                else os.path.join(self.MUSIC_DIR, file)
            )
            self.audio_handler.play_music(path_to_file)
            print(f"Playing music: {path_to_file}")
        else:
            print("No music file specified or available to play.")

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
            sleep(0.05)
            print(f"Playing sound: {path_to_file}")
        else:
            print("No sound file specified or available to play.")

    def say_text(self, text=None):
        text = text or self.settings.get("default_text", "Hello, I'm your video car!")
        self.audio_handler.text_to_speech(text)

    def move(self, direction, speed):
        print(f"Moving {direction} with speed {speed}")
        if direction == "forward":
            self.px.set_dir_servo_angle(0)
            self.px.forward(speed)
        elif direction == "backward":
            self.px.set_dir_servo_angle(0)
            self.px.backward(speed)
        elif direction == "left":
            self.px.set_dir_servo_angle(-30)
            self.px.forward(speed)
        elif direction == "right":
            self.px.set_dir_servo_angle(30)
            self.px.forward(speed)

    def set_servo_angle(self, angle):
        print(f"Setting servo angle to {angle} degrees")
        self.px.set_dir_servo_angle(angle)

    def set_cam_tilt_angle(self, angle):
        print(f"Setting camera tilt angle to {angle} degrees")
        self.px.set_cam_tilt_angle(angle)

    def set_cam_pan_angle(self, angle):
        print(f"Setting camera pan angle to {angle} degrees")
        self.px.set_cam_pan_angle(angle)

    def stop(self):
        print("Stopping")
        self.px.stop()

    async def start_server(self):
        async with websockets.serve(self.handle_message, "0.0.0.0", 8765):
            await asyncio.Future()  # Run forever

    def main(self):
        Vilib.camera_start(vflip=False, hflip=False)
        sleep(2)  # Allow the camera to start

        ip_address = self.get_ip_address()
        print(
            f"\nTo access the frontend, open your browser and navigate to http://{ip_address}:9000\n"
        )

        try:
            asyncio.run(self.start_server())
        except KeyboardInterrupt:
            print("\nquit ...")
            self.px.stop()
            Vilib.camera_close()

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't matter if it fails.
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
        except Exception:
            ip_address = "127.0.0.1"
        finally:
            s.close()
        return ip_address

    def list_files(self, directory: str):
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

    def save_file(self, file, directory):
        """
        Saves uploaded file to the specified directory.
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        file_path = os.path.join(directory, file.filename)
        file.save(file_path)
