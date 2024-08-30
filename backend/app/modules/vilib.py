import os
import threading
import asyncio
import time
from multiprocessing import Manager
from typing import Optional, List, Tuple
import subprocess
import cv2
import numpy as np
from app.config.logging_config import setup_logger
from app.config.paths import (
    DEFAULT_VIDEOS_PATH,
)

logger = setup_logger(__name__)

user = os.getlogin()
user_home = os.path.expanduser(f"~{user}")


CameraInfo = Tuple[int, str, Optional[str]]


class Vilib(object):
    camera_vflip = False
    camera_hflip = False
    camera_run = False

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
    camera_index: Optional[int] = None
    is_greyscale_camera = False
    starting = False
    target_fps = 30

    @staticmethod
    def get_device_info(device_path: str) -> str:
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--device", device_path, "--all"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout
        except Exception as e:
            return f"Error checking device {device_path}: {e}"

    @staticmethod
    def find_available_cameras() -> List[CameraInfo]:
        camera_indices: List[CameraInfo] = []

        video_devices = [f for f in os.listdir("/dev") if f.startswith("video")]
        for device in video_devices:
            device_path = os.path.join("/dev", device)
            index = int(device.replace("video", ""))
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    device_info = Vilib.get_device_info(device_path)
                    camera_indices.append((index, device_path, device_info))
                cap.release()

        return camera_indices

    @staticmethod
    def prioritize_cameras(available_cameras: List[CameraInfo]):
        color_cameras: List[CameraInfo] = []
        greyscale_cameras: List[CameraInfo] = []

        for index, device_path, device_info in available_cameras:
            if device_info and "8-bit Greyscale" in device_info:
                greyscale_cameras.append((index, device_path, device_info))
            else:
                color_cameras.append((index, device_path, device_info))

        if color_cameras:
            return color_cameras[0]
        elif greyscale_cameras:
            return greyscale_cameras[0]
        else:
            return None, None, None

    @staticmethod
    def read_camera(index: int, is_greyscale: bool) -> Optional[np.ndarray]:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                if is_greyscale:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                return frame
        return None

    @staticmethod
    def camera_loop():
        logger.info("Starting camera loop")

        Vilib.camera_index = 0
        Vilib.capture = cv2.VideoCapture(Vilib.camera_index)

        if not Vilib.capture.isOpened():
            Vilib.capture.release()
            logger.error(f"Failed to open camera at {Vilib.camera_index}.")
            return

        # set fixed fps
        Vilib.capture.set(cv2.CAP_PROP_FPS, Vilib.target_fps)

        fps = 0
        framecount = 0
        start_time = time.perf_counter()

        try:
            while Vilib.camera_run:
                ret, frame = Vilib.capture.read()
                if not ret:
                    logger.warning("Warning: Failed to read frame from camera.")
                    continue

                if Vilib.camera_vflip:
                    frame = cv2.flip(frame, 0)
                if Vilib.camera_hflip:
                    frame = cv2.flip(frame, 1)

                Vilib.img = frame
                # Calculate FPS
                framecount += 1
                elapsed_time = time.perf_counter() - start_time
                if elapsed_time > 1:
                    fps = round(framecount / elapsed_time, 1)
                    framecount = 0
                    start_time = time.perf_counter()

                # Draw FPS on frame
                if Vilib.draw_fps:
                    cv2.putText(
                        Vilib.img,
                        f"FPS: {fps}",
                        Vilib.fps_origin,
                        cv2.FONT_HERSHEY_SIMPLEX,
                        Vilib.fps_size,
                        Vilib.fps_color,
                        1,
                        cv2.LINE_AA,
                    )

                with threading.Lock():
                    Vilib.flask_img = Vilib.img.copy()
        except Exception as e:
            logger.error(f"Exception occurred in camera loop: {e}")
        finally:
            Vilib.capture.release()
            logger.info("Camera loop terminated and camera released.")

    @staticmethod
    def camera_start(vflip=False, hflip=False, fps=30):
        logger.info(f"Starting camera with vflip={vflip}, hflip={hflip}, fps={fps}")
        Vilib.camera_hflip = hflip
        Vilib.camera_vflip = vflip
        Vilib.target_fps = fps
        Vilib.camera_run = True
        Vilib.camera_thread = threading.Thread(target=Vilib.camera_loop, name="vilib")
        Vilib.camera_thread.daemon = False
        Vilib.camera_thread.start()

    @staticmethod
    def camera_close():
        logger.info("Closing camera")
        Vilib.camera_run = False
        if Vilib.camera_thread is not None:
            Vilib.camera_thread.join()

        Vilib.img = None
        Vilib.flask_img = None

    @staticmethod
    async def ensure_camera(vflip=False, hflip=False, fps=30):
        if not Vilib.camera_run:
            Vilib.camera_start(vflip, hflip, fps)

        while Vilib.img is None:
            logger.info("waiting for flask img")
            await asyncio.sleep(0.1)

    @staticmethod
    async def start_camera_and_wait_for_flask_img(vflip=False, hflip=False, fps=30):
        if not Vilib.camera_run:
            Vilib.camera_start(vflip, hflip, fps)

        while Vilib.flask_img is None:
            logger.info("waiting for flask img")
            await asyncio.sleep(0.1)

    @staticmethod
    async def take_photo(photo_name: str, path: str):
        logger.info(f"Taking photo '{photo_name}' at path {path}")
        if not os.path.exists(path):
            os.makedirs(name=path, mode=0o751, exist_ok=True)
            await asyncio.sleep(0.01)

        status = False
        for _ in range(5):
            if Vilib.img is not None:
                status = cv2.imwrite(os.path.join(path, photo_name + ".jpg"), Vilib.img)
                break
            else:
                await asyncio.sleep(0.01)
        else:
            status = False

        return status

        # record video

    # =================================================================
    rec_video_set = {}

    fourcc: int = cv2.VideoWriter_fourcc(*"XVID")  # type: ignore

    rec_video_set["fps"] = 30.0
    rec_video_set["framesize"] = (640, 480)
    rec_video_set["isColor"] = True

    rec_video_set["name"] = "default"
    rec_video_set["path"] = DEFAULT_VIDEOS_PATH

    rec_video_set["start_flag"] = False
    rec_video_set["stop_flag"] = False

    rec_thread = None

    @staticmethod
    def rec_video_work():
        if not os.path.exists(Vilib.rec_video_set["path"]):
            os.makedirs(name=Vilib.rec_video_set["path"], mode=0o751, exist_ok=True)
            time.sleep(0.01)
        video_out = cv2.VideoWriter(
            Vilib.rec_video_set["path"] + "/" + Vilib.rec_video_set["name"] + ".avi",
            Vilib.rec_video_set["fourcc"],
            Vilib.rec_video_set["fps"],
            Vilib.rec_video_set["framesize"],
            Vilib.rec_video_set["isColor"],
        )

        while True:
            if Vilib.rec_video_set["start_flag"] == True and Vilib.img is not None:
                video_out.write(Vilib.img)
            if Vilib.rec_video_set["stop_flag"] == True:
                video_out.release()
                Vilib.rec_video_set["start_flag"] = False
                break

    @staticmethod
    def rec_video_run():
        if Vilib.rec_thread != None:
            Vilib.rec_video_stop()
        Vilib.rec_video_set["stop_flag"] = False
        Vilib.rec_thread = threading.Thread(
            name="rec_video", target=Vilib.rec_video_work
        )
        Vilib.rec_thread.daemon = True
        Vilib.rec_thread.start()

    @staticmethod
    def rec_video_start():
        Vilib.rec_video_set["start_flag"] = True
        Vilib.rec_video_set["stop_flag"] = False

    @staticmethod
    def rec_video_pause():
        Vilib.rec_video_set["start_flag"] = False

    @staticmethod
    def rec_video_stop():
        Vilib.rec_video_set["start_flag"] = False
        Vilib.rec_video_set["stop_flag"] = True
        if Vilib.rec_thread != None:
            Vilib.rec_thread.join(3)
            Vilib.rec_thread = None

    # color detection
    # =================================================================
    @staticmethod
    def color_detect(color="red"):
        """
        :param color: could be red, green, blue, yellow , orange, purple
        """
        Vilib.color_detect_color = color
        from .color_detection import color_detect_work, color_obj_parameter

        Vilib.color_detect_work = color_detect_work
        Vilib.color_obj_parameter = color_obj_parameter
        Vilib.detect_obj_parameter["color_x"] = Vilib.color_obj_parameter["x"]
        Vilib.detect_obj_parameter["color_y"] = Vilib.color_obj_parameter["y"]
        Vilib.detect_obj_parameter["color_w"] = Vilib.color_obj_parameter["w"]
        Vilib.detect_obj_parameter["color_h"] = Vilib.color_obj_parameter["h"]
        Vilib.detect_obj_parameter["color_n"] = Vilib.color_obj_parameter["n"]

    @staticmethod
    def color_detect_func(img):
        if Vilib.color_detect_color is not None and Vilib.color_detect_color != "close":
            img = Vilib.color_detect_work(img, 640, 480, Vilib.color_detect_color)
            Vilib.detect_obj_parameter["color_x"] = Vilib.color_obj_parameter["x"]
            Vilib.detect_obj_parameter["color_y"] = Vilib.color_obj_parameter["y"]
            Vilib.detect_obj_parameter["color_w"] = Vilib.color_obj_parameter["w"]
            Vilib.detect_obj_parameter["color_h"] = Vilib.color_obj_parameter["h"]
            Vilib.detect_obj_parameter["color_n"] = Vilib.color_obj_parameter["n"]
        return img

    @staticmethod
    def close_color_detection():
        Vilib.color_detect_color = None

    # face detection
    # =================================================================
    @staticmethod
    def face_detect_switch(flag=False):
        Vilib.face_detect_sw = flag
        if Vilib.face_detect_sw:
            from .face_detection import (
                face_detect,
                face_obj_parameter,
                set_face_detection_model,
            )

            Vilib.face_detect_work = face_detect
            Vilib.set_face_detection_model = set_face_detection_model
            Vilib.face_obj_parameter = face_obj_parameter
            Vilib.detect_obj_parameter["human_x"] = Vilib.face_obj_parameter["x"]
            Vilib.detect_obj_parameter["human_y"] = Vilib.face_obj_parameter["y"]
            Vilib.detect_obj_parameter["human_w"] = Vilib.face_obj_parameter["w"]
            Vilib.detect_obj_parameter["human_h"] = Vilib.face_obj_parameter["h"]
            Vilib.detect_obj_parameter["human_n"] = Vilib.face_obj_parameter["n"]

    @staticmethod
    def face_detect_func(img):
        if Vilib.face_detect_sw:
            img = Vilib.face_detect_work(img, 640, 480)
            Vilib.detect_obj_parameter["human_x"] = Vilib.face_obj_parameter["x"]
            Vilib.detect_obj_parameter["human_y"] = Vilib.face_obj_parameter["y"]
            Vilib.detect_obj_parameter["human_w"] = Vilib.face_obj_parameter["w"]
            Vilib.detect_obj_parameter["human_h"] = Vilib.face_obj_parameter["h"]
            Vilib.detect_obj_parameter["human_n"] = Vilib.face_obj_parameter["n"]
        return img

    # traffic sign detection
    # =================================================================
    @staticmethod
    def traffic_detect_switch(flag=False):
        Vilib.traffic_detect_sw = flag
        if Vilib.traffic_detect_sw:
            from .traffic_sign_detection import (
                traffic_sign_detect,
                traffic_sign_obj_parameter,
            )

            Vilib.traffic_detect_work = traffic_sign_detect
            Vilib.traffic_sign_obj_parameter = traffic_sign_obj_parameter
            Vilib.detect_obj_parameter["traffic_sign_x"] = (
                Vilib.traffic_sign_obj_parameter["x"]
            )
            Vilib.detect_obj_parameter["traffic_sign_y"] = (
                Vilib.traffic_sign_obj_parameter["y"]
            )
            Vilib.detect_obj_parameter["traffic_sign_w"] = (
                Vilib.traffic_sign_obj_parameter["w"]
            )
            Vilib.detect_obj_parameter["traffic_sign_h"] = (
                Vilib.traffic_sign_obj_parameter["h"]
            )
            Vilib.detect_obj_parameter["traffic_sign_t"] = (
                Vilib.traffic_sign_obj_parameter["t"]
            )
            Vilib.detect_obj_parameter["traffic_sign_acc"] = (
                Vilib.traffic_sign_obj_parameter["acc"]
            )

    @staticmethod
    def traffic_detect_fuc(img):
        if Vilib.traffic_detect_sw:
            img = Vilib.traffic_detect_work(img, border_rgb=(255, 0, 0))
            Vilib.detect_obj_parameter["traffic_sign_x"] = (
                Vilib.traffic_sign_obj_parameter["x"]
            )
            Vilib.detect_obj_parameter["traffic_sign_y"] = (
                Vilib.traffic_sign_obj_parameter["y"]
            )
            Vilib.detect_obj_parameter["traffic_sign_w"] = (
                Vilib.traffic_sign_obj_parameter["w"]
            )
            Vilib.detect_obj_parameter["traffic_sign_h"] = (
                Vilib.traffic_sign_obj_parameter["h"]
            )
            Vilib.detect_obj_parameter["traffic_sign_t"] = (
                Vilib.traffic_sign_obj_parameter["t"]
            )
            Vilib.detect_obj_parameter["traffic_sign_acc"] = (
                Vilib.traffic_sign_obj_parameter["acc"]
            )
        return img

    # qrcode recognition
    # =================================================================
    @staticmethod
    def qrcode_detect_switch(flag=False):
        Vilib.qrcode_detect_sw = flag
        if Vilib.qrcode_detect_sw:
            from .qrcode_recognition import qrcode_obj_parameter, qrcode_recognize

            Vilib.qrcode_recognize = qrcode_recognize
            Vilib.qrcode_obj_parameter = qrcode_obj_parameter
            Vilib.detect_obj_parameter["qr_x"] = Vilib.qrcode_obj_parameter["x"]
            Vilib.detect_obj_parameter["qr_y"] = Vilib.qrcode_obj_parameter["y"]
            Vilib.detect_obj_parameter["qr_w"] = Vilib.qrcode_obj_parameter["w"]
            Vilib.detect_obj_parameter["qr_h"] = Vilib.qrcode_obj_parameter["h"]
            Vilib.detect_obj_parameter["qr_data"] = Vilib.qrcode_obj_parameter["data"]
            Vilib.detect_obj_parameter["qr_list"] = Vilib.qrcode_obj_parameter["list"]

    @staticmethod
    def qrcode_detect_func(img):
        if Vilib.qrcode_detect_sw:
            img = Vilib.qrcode_recognize(img, border_rgb=(255, 0, 0))
            Vilib.detect_obj_parameter["qr_x"] = Vilib.qrcode_obj_parameter["x"]
            Vilib.detect_obj_parameter["qr_y"] = Vilib.qrcode_obj_parameter["y"]
            Vilib.detect_obj_parameter["qr_w"] = Vilib.qrcode_obj_parameter["w"]
            Vilib.detect_obj_parameter["qr_h"] = Vilib.qrcode_obj_parameter["h"]
            Vilib.detect_obj_parameter["qr_data"] = Vilib.qrcode_obj_parameter["data"]
        return img

    # image classification
    # =================================================================
    @staticmethod
    def image_classify_switch(flag=False):
        from .image_classification import image_classification_obj_parameter

        Vilib.image_classify_sw = flag
        Vilib.image_classification_obj_parameter = image_classification_obj_parameter

    @staticmethod
    def image_classify_set_model(path):
        if not os.path.exists(path):
            raise ValueError("incorrect model path ")
        Vilib.image_classification_model = path

    @staticmethod
    def image_classify_set_labels(path):
        if not os.path.exists(path):
            raise ValueError("incorrect labels path ")
        Vilib.image_classification_labels = path

    @staticmethod
    def image_classify_fuc(img):
        if Vilib.image_classify_sw == True:
            from .image_classification import classify_image

            img = classify_image(
                image=img,
                model=Vilib.image_classification_model,
                labels=Vilib.image_classification_labels,
            )
        return img

    # objects detection
    # =================================================================
    @staticmethod
    def object_detect_switch(flag=False):
        Vilib.objects_detect_sw = flag
        from .objects_detection import object_detection_list_parameter

        Vilib.object_detection_list_parameter = object_detection_list_parameter

    @staticmethod
    def object_detect_set_model(path):
        if not os.path.exists(path):
            raise ValueError("incorrect model path ")
        Vilib.objects_detection_model = path

    @staticmethod
    def object_detect_set_labels(path):
        if not os.path.exists(path):
            raise ValueError("incorrect labels path ")
        Vilib.objects_detection_labels = path

    @staticmethod
    def object_detect_fuc(img):
        if Vilib.objects_detect_sw == True:
            # print('detect_objects starting')
            from .objects_detection import detect_objects

            img = detect_objects(
                image=img,
                model=Vilib.objects_detection_model,
                labels=Vilib.objects_detection_labels,
            )
        return img

    # hands detection
    # =================================================================
    @staticmethod
    def hands_detect_switch(flag=False):
        from .hands_detection import DetectHands

        Vilib.detect_hands = DetectHands()
        Vilib.hands_detect_sw = flag

    @staticmethod
    def hands_detect_fuc(img):
        if Vilib.hands_detect_sw == True:
            turp = Vilib.detect_obj_parameter["hands_joints"] = Vilib.detect_hands.work(
                image=img
            )
            if turp:
                img, Vilib.detect_obj_parameter["hands_joints"] = turp
        return img

    # pose detection
    # =================================================================
    @staticmethod
    def pose_detect_switch(flag=False):
        from .pose_detection import DetectPose

        Vilib.pose_detect = DetectPose()
        Vilib.pose_detect_sw = flag

    @staticmethod
    def pose_detect_fuc(img):
        if Vilib.pose_detect_sw == True:
            turp = Vilib.pose_detect.work(image=img)
            if turp:
                img, Vilib.detect_obj_parameter["body_joints"] = turp
        return img
