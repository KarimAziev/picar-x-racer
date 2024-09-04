import asyncio
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Generator, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import torch
from app.config.paths import (
    CAT_FACE_CASCADE_PATH,
    CAT_FACE_EXTENDED_CASCADE_PATH,
    HUMAN_FACE_CASCADE_PATH,
    HUMAN_FULL_BODY_CASCADE_PATH,
)
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from app.util.video_utils import enhance_frame

# Constants for target width and height of video streams
TARGET_WIDTH = 640
TARGET_HEIGHT = 480

CameraInfo = Tuple[int, str, Optional[str]]


class CameraController(metaclass=SingletonMeta):
    """
    CameraController is a singleton class responsible for managing camera operations, including
    starting the camera, capturing frames, flipping frames, encoding frames into different formats,
    and streaming video frames to clients.
    """

    def __init__(self, max_workers=4, target_fps=30):
        self.max_workers = max_workers
        self.logger = Logger(name=__name__)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.executor_shutdown = False
        self.active_clients = 0
        self.target_fps = target_fps
        self.camera_index = 0
        self.camera_vflip = False
        self.camera_hflip = False
        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.flask_img: Optional[np.ndarray] = None
        self.video_devices: List[str] = []
        self.failed_camera_indexes: List[int] = []
        self.lock = threading.Lock()
        self.cat_face_cascade = cv2.CascadeClassifier(CAT_FACE_CASCADE_PATH)
        self.cat_face_extended_cascade = cv2.CascadeClassifier(
            CAT_FACE_EXTENDED_CASCADE_PATH
        )
        self.human_face_cascade = cv2.CascadeClassifier(HUMAN_FACE_CASCADE_PATH)
        self.human_full_body_cascade = cv2.CascadeClassifier(
            HUMAN_FULL_BODY_CASCADE_PATH
        )

        self.yolo_model = torch.hub.load("ultralytics/yolov5", "yolov5s")

    def detect_cat_faces(self, frame: np.ndarray) -> np.ndarray:
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.yolo_model(img_rgb)

        for result in results.xyxy[0]:
            x1, y1, x2, y2, conf, cls = result
            if self.yolo_model.names[int(cls)] == "cat":
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{self.yolo_model.names[int(cls)]} {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

        return frame

    def detect_full_body_faces(self, frame: np.ndarray) -> np.ndarray:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cat_faces = self.human_full_body_cascade.detectMultiScale(
            gray_frame, scaleFactor=1.1, minNeighbors=5
        )
        for x, y, w, h in cat_faces:
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        return frame

    def detect_cat_extended_faces(self, frame: np.ndarray) -> np.ndarray:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cat_faces = self.cat_face_extended_cascade.detectMultiScale(
            gray_frame, scaleFactor=1.1, minNeighbors=5
        )
        for x, y, w, h in cat_faces:
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        return frame

    def detect_human_faces(self, frame: np.ndarray) -> np.ndarray:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        human_faces = self.human_face_cascade.detectMultiScale(
            gray_frame, scaleFactor=1.1, minNeighbors=5
        )
        for x, y, w, h in human_faces:
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return frame

    def async_generate_video_stream(
        self,
        format=".png",
        encode_params: Sequence[int] = [],
        frame_enhancer: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        height: Optional[int] = None,
        detection_func: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    ):
        self.active_clients += 1
        self.logger.info(f"Active Clients: {self.active_clients}")

        try:
            while True:
                with self.lock:
                    img_copy = (
                        self.flask_img.copy() if self.flask_img is not None else None
                    )

                if img_copy is not None:
                    if detection_func:
                        img_copy = detection_func(img_copy)

                    if self.executor_shutdown:
                        self.logger.warning(
                            "Executor already shutdown, cannot submit new task."
                        )
                        break
                    future = self.executor.submit(
                        self.encode,
                        img_copy,
                        format,
                        encode_params,
                        frame_enhancer,
                        height,
                    )
                    encoded_frame = future.result()
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_frame + b"\r\n"
                else:
                    self.logger.debug("Flask image is None, skipping frame.")
        finally:
            self.active_clients -= 1
            self.logger.info(f"Active Clients: {self.active_clients}")
            if self.active_clients == 0 and not self.executor_shutdown:
                self.executor.shutdown(wait=True, cancel_futures=True)
                self.executor_shutdown = True
                self.logger.info("Executor shut down due to no active clients.")
                self.camera_close()  # Close the camera when no active clients

    def generate_high_quality_stream_jpg_cat_recognize(
        self,
    ) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(
            ".jpg",
            [cv2.IMWRITE_JPEG_QUALITY, 100],
            None,
            detection_func=self.detect_cat_faces,
        )

    def generate_high_quality_stream_jpg_cat_extended_recognize(
        self,
    ) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(
            ".jpg",
            [cv2.IMWRITE_JPEG_QUALITY, 100],
            None,
            detection_func=self.detect_cat_extended_faces,
        )

    def generate_high_quality_stream_jpg_human_recognize(
        self,
    ) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(
            ".jpg",
            [cv2.IMWRITE_JPEG_QUALITY, 100],
            None,
            detection_func=self.detect_human_faces,
        )

    def generate_high_quality_stream_jpg_human_full_body_recognize(
        self,
    ) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(
            ".jpg",
            [cv2.IMWRITE_JPEG_QUALITY, 100],
            None,
            detection_func=self.detect_full_body_faces,
        )

    @staticmethod
    def height_to_width(height: int):
        aspect_ratio = TARGET_WIDTH / TARGET_HEIGHT
        width = aspect_ratio * height
        return int(width)

    @staticmethod
    def get_device_info(device_path: str) -> str:
        """
        Get detailed information of the video device using `v4l2-ctl` command.

        Args:
            device_path (str): Path to the video device.

        Returns:
            str: Detailed information about the video device.
        """
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

    def find_camera_index(self):
        """
        Find an available camera index by iterating over video devices and checking their availability.

        Returns:
            CameraInfo: Tuple containing index, device path, and device information of the selected camera.
        """
        greyscale_cameras: List[CameraInfo] = []

        self.video_devices = self.video_devices or [
            f for f in os.listdir("/dev") if f.startswith("video")
        ]
        for device in self.video_devices:
            device_path = os.path.join("/dev", device)
            index = int(device.replace("video", ""))
            if index not in self.failed_camera_indexes:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is None:
                        self.failed_camera_indexes.append(index)
                        self.video_devices.remove(device)
                    else:
                        device_info = CameraController.get_device_info(device_path)
                        if device_info and "8-bit Greyscale" in device_info:
                            greyscale_cameras.append((index, device_path, device_info))
                        else:
                            cap.release()
                            return (index, device_path, device_info)
                    cap.release()

        return greyscale_cameras[0]

    def camera_thread_func_setup(self):
        """
        Set up the camera for capturing frames by configuring width, height, and FPS.

        Returns:
            cv2.VideoCapture: Opened video capture object.
        """
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            cap.release()
            self.logger.error(f"Failed to open camera at {self.camera_index}.")
            self.failed_camera_indexes.append(self.camera_index)
            new_index, _, device_info = self.find_camera_index()
            if isinstance(new_index, int):
                self.logger.error(
                    f"Failed to open camera at {self.camera_index}, trying {new_index}: {device_info}"
                )
                self.camera_index = new_index
                return self.camera_thread_func_setup()
            else:
                self.logger.error(f"Failed to open camera at {self.camera_index}.")
                raise SystemExit(
                    f"Exiting: Camera {self.camera_index} couldn't be opened."
                )

        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1200)
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 800)

        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        return cap

    def camera_thread_func(self):
        """
        Camera loop function that continuously captures frames, performs flips if required,
        and updates the current frame.
        """
        self.logger.info(f"Starting camera loop with camera index {self.camera_index}")
        cap = self.camera_thread_func_setup()

        failed_counter = 0
        max_failed_attempt_count = 10

        try:
            while self.camera_run:
                ret, frame = cap.read()
                if not ret:
                    if failed_counter < max_failed_attempt_count:
                        failed_counter += 1
                        self.logger.error("Failed to read frame from camera.")
                        continue
                    else:
                        self.failed_camera_indexes.append(self.camera_index)
                        cap.release()
                        new_index, _, device_info = self.find_camera_index()
                        if isinstance(new_index, int):
                            self.logger.info(
                                f"Camera index {self.camera_index} is failed, trying {new_index}: {device_info}"
                            )
                            self.camera_index = new_index
                            cap = self.camera_thread_func_setup()
                            failed_counter = 0
                            continue
                else:
                    failed_counter = 0

                if self.camera_vflip:
                    frame = cv2.flip(frame, 0)
                if self.camera_hflip:
                    frame = cv2.flip(frame, 1)

                self.img = frame

                with self.lock:
                    self.flask_img = frame.copy()

        except Exception as e:
            self.logger.error(f"Exception occurred in camera loop: {e}")
        finally:
            cap.release()
            with self.lock:
                self.flask_img = None
            self.logger.info("Camera loop terminated and camera released.")

    def camera_start(self, vflip=False, hflip=False, fps=30):
        """
        Start the camera capturing loop in a separate thread.

        Args:
            vflip (bool): Flag to determine vertical flip of the camera frame.
            hflip (bool): Flag to determine horizontal flip of the camera frame.
            fps (int): Frames per second for the camera.
        """
        self.logger.info(
            f"Starting camera with vflip={vflip}, hflip={hflip}, fps={fps}"
        )
        self.camera_hflip = hflip
        self.camera_vflip = vflip
        self.target_fps = fps
        self.camera_run = True

        self.camera_thread = threading.Thread(target=self.camera_thread_func)
        self.camera_thread.start()

    def camera_close(self):
        """
        Close the camera and clean up resources.
        """
        self.logger.info("Closing camera")
        self.camera_run = False
        if hasattr(self, "camera_thread"):
            self.camera_thread.join()
        with self.lock:
            self.flask_img = None

    def shutdown(self):
        """
        Close the camera and clean up resources.
        """
        self.logger.info("Closing camera")
        self.camera_close()

        if not self.executor_shutdown:
            self.executor.shutdown(wait=True)
            self.executor_shutdown = True

    async def restart(self):
        await self.start_camera_and_wait_for_flask_img()
        if self.executor_shutdown:
            self.recreate_executor()

    def recreate_executor(self):
        """
        Recreate the ThreadPoolExecutor if it has been shut down.
        """
        if self.executor_shutdown:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self.executor_shutdown = False

    async def start_camera_and_wait_for_flask_img(
        self, vflip=False, hflip=False, fps=30
    ):
        """
        Asynchronously start the camera and wait for the Flask image to be available.

        Args:
            vflip (bool): Flag to determine vertical flip of the camera frame.
            hflip (bool): Flag to determine horizontal flip of the camera frame.
            fps (int): Frames per second for the camera.
        """
        if not self.camera_run:
            self.camera_start(vflip, hflip, fps)

        while True:
            with self.lock:
                if self.flask_img is not None:
                    break
            self.logger.debug("waiting for flask img")
            await asyncio.sleep(0.1)

    async def take_photo(self, photo_name: str, path: str) -> bool:
        """
        Asynchronously take a photo and save it to the specified path.

        Args:
            photo_name (str): Name of the photo file.
            path (str): Directory path to save the photo.

        Returns:
            bool: Status indicating success or failure of taking the photo.
        """
        self.logger.info(f"Taking photo '{photo_name}' at path {path}")
        if not os.path.exists(path):
            os.makedirs(name=path, mode=0o751, exist_ok=True)
            await asyncio.sleep(0.01)

        status = False
        for _ in range(5):
            with self.lock:
                img_copy = self.img.copy() if self.img is not None else None

            if img_copy is not None:
                status = cv2.imwrite(os.path.join(path, photo_name), img_copy)
                break
            else:
                await asyncio.sleep(0.01)
        else:
            status = False

        return status

    def convert_listproxy_to_array(self, listproxy_obj):
        """
        Convert a ListProxy object to a numpy array.

        Args:
            listproxy_obj: A ListProxy object to be converted.

        Returns:
            np.ndarray: Converted numpy array.

        Raises:
            ValueError: If the ListProxy object is None.
        """
        if listproxy_obj is None:
            self.logger.error("ListProxy object is None")
            raise ValueError("ListProxy object is None")
        np_array = np.array(listproxy_obj, dtype=np.uint8)
        return np_array

    def get_frame(self) -> bytes:
        """
        Get the current frame as a JPEG-encoded byte array.

        Returns:
            bytes: JPEG-encoded byte array of the current frame.

        Raises:
            ValueError: If the Flask image is None.
        """
        with self.lock:
            frame_array = self.flask_img.copy() if self.flask_img is not None else None

        if frame_array is None:
            self.logger.error("get_frame: Flask image is None, cannot get frame.")
            raise ValueError("Flask image is None")

        _, buffer = cv2.imencode(".jpg", frame_array)
        return buffer.tobytes()

    def get_png_frame(self) -> bytes:
        """
        Get the current frame as a PNG-encoded byte array.

        Returns:
            bytes: PNG-encoded byte array of the current frame.

        Raises:
            ValueError: If the Flask image is None.
        """
        with self.lock:
            frame_array = self.flask_img.copy() if self.flask_img is not None else None

        if frame_array is None:
            self.logger.error("get_png_frame: Flask image is None, cannot get frame.")
            raise ValueError("Flask image is None")

        _, buffer = cv2.imencode(".png", frame_array)
        return buffer.tobytes()

    def resize_and_encode(
        self, frame: np.ndarray, width: int, height: int, format=".jpg", quality=100
    ):
        """
        Resize the frame and encode it to the specified format.

        Args:
            frame (np.ndarray): Frame to be resized and encoded.
            width (int): Width to resize the frame.
            height (int): Height to resize the frame.
            format (str): Encoding format (default is ".jpg").
            quality (int): Quality of JPEG encoding (default is 100).

        Returns:
            bytes: Encoded frame as a byte array.
        """
        resized_frame = cv2.resize(
            frame, (width, height), interpolation=cv2.INTER_CUBIC
        )
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality] if format == ".jpg" else []
        _, buffer = cv2.imencode(format, resized_frame, encode_params)
        return buffer.tobytes()

    def encode(
        self,
        frame_array: np.ndarray,
        format=".jpg",
        params: Sequence[int] = [],
        frame_enhancer: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        height: Optional[int] = None,
    ):
        """
        Encode the frame array to the specified format.

        Args:
            frame_array (np.ndarray): Frame array to be encoded.
            format (str): Encoding format (default is ".jpg").

        Returns:
            bytes: Encoded frame as a byte array.
        """
        width = CameraController.height_to_width(height) if height else None

        if frame_enhancer:
            frame_array = frame_enhancer(frame_array)

        if height and width:
            frame = cv2.resize(frame_array, (width, height))
        else:
            frame = frame_array

        _, buffer = cv2.imencode(format, frame, params)
        return buffer.tobytes()

    def generate_high_quality_stream_jpg(self) -> Generator[bytes, None, None]:
        """
        Generate a high-quality video stream with target width and height.

        Returns:
            Generator[bytes, None, None]: High-quality video stream.
        """
        return self.async_generate_video_stream(".jpg", [cv2.IMWRITE_JPEG_QUALITY, 100])

    def generate_medium_quality_stream_jpg(self) -> Generator[bytes, None, None]:
        """
        Generate a medium-quality video stream with JPEG format.

        Returns:
            Generator[bytes, None, None]: Medium-quality video stream.
        """
        return self.async_generate_video_stream(".jpg", [cv2.IMWRITE_JPEG_QUALITY, 95])

    def generate_extra_high_quality_stream_jpg(self) -> Generator[bytes, None, None]:
        """
        Generate extra high-quality video stream with target width and height.

        Returns:
            Generator[bytes, None, None]: High-quality video stream.
        """
        return self.async_generate_video_stream(
            ".jpg", [cv2.IMWRITE_JPEG_QUALITY, 100], enhance_frame
        )

    def generate_low_quality_stream_jpg(self) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(".jpg", [cv2.IMWRITE_JPEG_QUALITY, 80])

    def generate_extra_low_quality_stream_jpg(self) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(".jpg", [cv2.IMWRITE_JPEG_QUALITY, 20])

    def generate_low_quality_stream_png(self) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(".png", [])
