import os
import cv2
import time
import threading
import numpy as np
from typing import Optional
from multiprocessing import Manager


class Vilib(object):
    camera_vflip = False
    camera_hflip = False
    camera_run = False

    flask_thread = None
    camera_thread = None
    flask_start = False
    capture = None

    qrcode_display_thread = None
    qrcode_making_completed = False
    qrcode_img = Manager().list(range(1))
    qrcode_img_encode = None
    qrcode_win_name = "qrcode"

    img: Optional[np.ndarray] = None
    flask_img: Optional[np.ndarray] = None

    Windows_Name = "webcam"
    imshow_flag = False
    web_display_flag = False
    imshow_qrcode_flag = False
    web_qrcode_flag = False

    draw_fps = False
    fps_origin = (640 - 105, 20)
    fps_size = 0.6
    fps_color = (255, 255, 255)

    detect_obj_parameter = {}
    color_detect_color = None
    face_detect_sw = False
    hands_detect_sw = False
    pose_detect_sw = False
    image_classify_sw = False
    image_classification_model = None
    image_classification_labels = None
    objects_detect_sw = False
    objects_detection_model = None
    objects_detection_labels = None
    qrcode_detect_sw = False
    traffic_detect_sw = False

    @staticmethod
    def camera_loop():
        Vilib.capture = cv2.VideoCapture(0)
        if not Vilib.capture.isOpened():
            raise RuntimeError("Error: Webcam not found or unable to open.")

        while Vilib.camera_run:
            ret, frame = Vilib.capture.read()
            if not ret:
                continue

            if Vilib.camera_vflip:
                frame = cv2.flip(frame, 0)
            if Vilib.camera_hflip:
                frame = cv2.flip(frame, 1)

            Vilib.img = frame
            Vilib.flask_img = frame

            # Display on desktop
            if Vilib.imshow_flag:
                cv2.imshow(Vilib.Windows_Name, frame)
                cv2.waitKey(1)

            time.sleep(0.033)  # ~30 FPS

        Vilib.capture.release()
        cv2.destroyAllWindows()

    @staticmethod
    def camera_start(vflip=False, hflip=False):
        print(f"Starting camera with vflip={vflip}, hflip={hflip}")
        Vilib.camera_hflip = hflip
        Vilib.camera_vflip = vflip
        Vilib.camera_run = True
        Vilib.camera_thread = threading.Thread(target=Vilib.camera_loop, name="vilib")
        Vilib.camera_thread.daemon = False
        Vilib.camera_thread.start()

    @staticmethod
    def camera_close():
        print("Closing camera")
        if Vilib.camera_thread is not None:
            Vilib.camera_run = False
            Vilib.camera_thread.join()

    @staticmethod
    def display(local=True, web=True):
        print(f"Displaying camera feed with local={local}, web={web}")
        Vilib.imshow_flag = local

    @staticmethod
    def take_photo(photo_name, path):
        print(f"Taking photo '{photo_name}' at path {path}")
        if not os.path.exists(path):
            os.makedirs(name=path, mode=0o751, exist_ok=True)
            time.sleep(0.01)
        status = False
        for _ in range(5):
            if Vilib.img is not None:
                status = cv2.imwrite(os.path.join(path, photo_name + ".jpg"), Vilib.img)
                break
            else:
                time.sleep(0.01)
        else:
            status = False

        return status

    @staticmethod
    def show_fps(color=None, fps_size=None, fps_origin=None):
        if color is not None:
            Vilib.fps_color = color
        if fps_size is not None:
            Vilib.fps_size = fps_size
        if fps_origin is not None:
            Vilib.fps_origin = fps_origin
        Vilib.draw_fps = True

    @staticmethod
    def hide_fps():
        Vilib.draw_fps = False
