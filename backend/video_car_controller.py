import os
import json
import asyncio
from time import sleep, strftime, localtime, time
from os import geteuid, getlogin, path, environ
from audio_handler import AudioHandler
from flask import Flask, send_from_directory, Response, current_app
import numpy as np
import websockets
import threading
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
        self.status = "stop"

        self.music_path = environ.get('MUSIC_PATH', "../musics/robomusic.mp3")
        self.sound_path = environ.get('SOUND_PATH', "../sounds/directives.wav")

        # Initialize Vilib camera
        self.camera_thread = None
        self.vilib_img = np.zeros((480, 640, 3), dtype=np.uint8)

        # Drawing FPS on the image
        self.draw_fps = True
        self.start_time = time()

    async def handle_message(self, websocket, path):
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

            action = data.get("action")
            print(data.get('action', 'no action'))
            if action == "move":
                self.move(data.get('direction'), data.get('speed', 0))
            elif action == "setServo":
                self.set_servo_angle(data.get('angle', 0))
            elif action == "stop":
                self.stop()
            elif action == "setCamTiltAngle":
                self.set_cam_tilt_angle(data.get('angle', 0))
            elif action == "setCamPanAngle":
                self.set_cam_pan_angle(data.get('angle', 0))
            elif action == "playMusic":
                self.play_music()
            elif action == "playSound":
                self.play_sound()
            elif action == "sayText":
                self.say_text(data.get('text', ""))
            elif action == "takePhoto":
                self.take_photo()

    def take_photo(self):
        _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
        name = "photo_%s" % _time
        photo_path = f"{self.user_home}/Pictures/picar-x/"
        self.Vilib.take_photo(name, photo_path)
        print("\nphoto saved as %s%s.jpg" % (photo_path, name))

    def play_music(self):
        self.audio_handler.play_music(self.music_path)

    def play_sound(self):
        self.audio_handler.play_sound(self.sound_path)
        sleep(0.05)

    def say_text(self, text):
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

    def vilib_camera_thread(self):
        self.Vilib.camera_start(vflip=False, hflip=False)
        self.camera_thread = threading.Thread(target=self.capture_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()

    def capture_loop(self):
        while True:
            try:
                if not isinstance(self.Vilib.flask_img, list) or len(self.Vilib.flask_img) == 1:
                    print(f"Invalid Image Size: {len(self.Vilib.flask_img)}")
                    sleep(0.1)  # Allow time for the camera to capture the image
                    continue  # Wait until the flask_img is populated correctly
                self.vilib_img = convert_listproxy_to_array(self.Vilib.flask_img)
                if self.draw_fps:
                    self.draw_fps_text()
                print(f"Frame captured with shape: {self.vilib_img.shape} and dtype: {self.vilib_img.dtype}")
            except Exception as e:
                print(f"Error in capture_loop: {e}")

    def draw_fps_text(self):
        elapsed_time = time() - self.start_time
        self.start_time = time()
        fps = int(1 / elapsed_time)
        self.vilib_img = np.array(self.vilib_img, dtype=np.uint8)  # Ensure it is a numpy array
        cv2.putText(self.vilib_img, f"FPS: {fps}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    async def start_server(self):
        async with websockets.serve(self.handle_message, "0.0.0.0", 8765):
            await asyncio.Future()  # Run forever

    def main(self):
        self.Vilib.camera_start(vflip=False, hflip=False)
        sleep(2)  # Allow the camera to start

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
        frame_array = convert_listproxy_to_array(Vilib.flask_img)
        encoded, buffer = cv2.imencode('.jpg', frame_array)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        sleep(0.1)

def run_flask(vc):
    app.config['vc'] = vc
    app.run(host='0.0.0.0', port=9000, threaded=True, debug=False)