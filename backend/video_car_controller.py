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

            if "key" in data:
                self.handle_key_press(data["key"])
            elif "photo" in data and data["photo"] == "take":
                self.take_photo()
            elif "music" in data:
                self.handle_music_control(data["music"])
            elif "sound" in data:
                self.handle_sound_control(data["sound"])
            elif "speech" in data:
                self.audio_handler.text_to_speech(data["speech"])

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

    def handle_key_press(self, key):
        if key == " ":
            self.status = "stop"
            self.target_speed = 0
            self.moving = False
            self.target_steering_angle = 0
        elif key == "=":
            if self.target_speed <= 90:
                self.target_speed += 10
        elif key == "-":
            if self.target_speed >= 10:
                self.target_speed -= 10
            if self.target_speed == 0:
                self.status = "stop"
        elif key == "w":
            self.status = "forward"
            self.target_speed = 60
            self.moving = True
        elif key == "s":
            self.status = "backward"
            self.target_speed = 60
            self.moving = True
        elif key == "a":
            self.target_steering_angle = -30
        elif key == "d":
            self.target_steering_angle = 30
        elif key == "UP":
            self.cam_tilt_angle = min(35, self.cam_tilt_angle + 5)
            self.px.set_cam_tilt_angle(self.cam_tilt_angle)
        elif key == "DOWN":
            self.cam_tilt_angle = max(-35, self.cam_tilt_angle - 5)
            self.px.set_cam_tilt_angle(self.cam_tilt_angle)
        elif key == "LEFT":
            self.cam_pan_angle = max(-35, self.cam_pan_angle - 5)
            self.px.set_cam_pan_angle(self.cam_pan_angle)
        elif key == "RIGHT":
            self.cam_pan_angle = min(35, self.cam_pan_angle + 5)
            self.px.set_cam_pan_angle(self.cam_pan_angle)

    async def start_server(self):
        async with websockets.serve(self.handle_message, "0.0.0.0", 8765):
            await asyncio.Future()  # Run forever

    def main(self):
        self.Vilib.camera_start(vflip=False, hflip=False)
        self.Vilib.display(local=False, web=True)
        sleep(2)  # wait for startup

        try:
            asyncio.run(self.start_server())
        except KeyboardInterrupt:
            print("\nquit ...")
            self.px.stop()
            self.Vilib.camera_close()

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
