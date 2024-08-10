import os
import json
import asyncio
from time import sleep, strftime, localtime
from os import geteuid, getlogin, path, environ
from audio_handler import AudioHandler
from flask import Flask, send_from_directory, Response
import numpy as np
import websockets
import cv2
import socket

app = Flask(__name__, static_folder='../front-end/dist/assets', template_folder='../front-end/dist')
is_os_raspberry = os.uname().nodename == "raspberrypi"

if is_os_raspberry:
     print("OS is raspberrypi")
     from picarx import Picarx
     from vilib import Vilib
     from robot_hat.utils import reset_mcu
else:
     from stubs import FakePicarx as Picarx
     from stubs import FakeVilib as Vilib
     from stubs import fake_reset_mcu as reset_mcu
class VideoCarController:
    def __init__(self):
        self.is_os_raspberry = is_os_raspberry

        self.Picarx = Picarx
        self.Vilib = Vilib
        self.reset_mcu = reset_mcu
        self.reset_mcu()
        sleep(0.2)  # Allow the MCU to reset

        self.user = getlogin()
        self.user_home = path.expanduser(f"~{self.user}")

        self.px = self.Picarx()
        self.audio_handler = AudioHandler()

        if geteuid() != 0 and self.is_os_raspberry:
            print(f"\033[0;33m{'The program needs to be run using sudo, otherwise there may be no sound.'}\033[0m")
        self.speed = 0
        self.target_speed = 0
        self.status = "stop"
        self.flag_bgm = False
        self.cam_tilt_angle = 0
        self.cam_pan_angle = 0
        self.steering_angle = 0
        self.target_steering_angle = 0
        self.moving = False
        self.deceleration_timer = None

        self.music_path = environ.get('MUSIC_PATH', "../musics/robomusic.mp3")
        self.sound_path = environ.get('SOUND_PATH', "../sounds/directives.wav")

        self.deceleration_timer = None

    async def handle_message(self, websocket, _path):
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

            if "action" in data:
                action = data["action"]
                if action == "move":
                    direction = data.get('direction', None)
                    speed = data.get('speed', 0)
                    if direction and direction in ["forward", "backward"]:
                        self.move(direction, speed)
                elif action == "setServo":
                    angle = data.get('angle', 0)
                    self.px.set_dir_servo_angle(angle)
                elif action == "stop":
                    self.px.stop()
                elif action == "setCamTiltAngle":
                    angle = data.get("angle", 0)
                    self.set_cam_tilt_angle(angle)
                elif action == "setCamPanAngle":
                    angle = data.get("angle", 0)
                    self.set_cam_pan_angle(angle)

    def take_photo(self):
        _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
        name = "photo_%s" % _time
        photo_path = f"{self.user_home}/Pictures/picar-x/"
        self.Vilib.take_photo(name, photo_path)
        print("\nphoto saved as %s%s.jpg" % (photo_path, name))

    def handle_music_control(self, action):
        if action == "play":
            self.flag_bgm = True
            self.audio_handler.play_music(self.music_path)
        elif action == "stop":
            self.flag_bgm = False
            self.audio_handler.stop_music()

    def handle_sound_control(self, action):
        if action == "play":
            self.audio_handler.play_sound(self.sound_path)
            sleep(0.05)

    def move(self, direction, speed):
        print(f"Moving {direction} with speed {speed}")
        if direction == "forward":
            self.px.forward(speed)
        elif direction == "backward":
            self.px.backward(speed)

    def set_cam_tilt_angle(self, angle):
        print(f"Setting camera tilt angle to {angle} degrees")
        self.cam_tilt_angle = angle
        self.px.set_cam_tilt_angle(self.cam_tilt_angle)

    def set_cam_pan_angle(self, angle):
        print(f"Setting camera pan angle to {angle} degrees")
        self.cam_pan_angle = angle
        self.px.set_cam_pan_angle(self.cam_pan_angle)

    async def start_server(self):
        async with websockets.serve(self.handle_message, "0.0.0.0", 8765):
            await asyncio.Future()  # Run forever

    def main(self):
        self.Vilib.camera_start(vflip=False, hflip=False)
        sleep(2)  # wait for startup

        ip_address = self.get_ip_address()
        print(f"\nTo access the frontend, open your browser and navigate to http://{ip_address}:9000\n")

        try:
            asyncio.run(self.start_server())
        except KeyboardInterrupt:
            print("\nquit ...")
            self.px.stop()
            self.Vilib.camera_close()

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

@app.route('/')
def index():
    template_folder = app.template_folder
    if isinstance(template_folder, str):
        return send_from_directory(template_folder, 'index.html')
    raise ValueError("Template folder is not a valid path.")

@app.route('/mjpg')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

def convert_listproxy_to_array(listproxy_obj):
    return np.array(listproxy_obj, dtype=np.uint8).reshape((480, 640, 3))

def gen():
    while True:
        frame_array = convert_listproxy_to_array(Vilib.flask_img)  # Convert ListProxy to numpy array
        encoded, buffer = cv2.imencode('.jpg', frame_array)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        sleep(0.1)

def run_flask():
    app.run(host='0.0.0.0', port=9000, threaded=True, debug=False)
