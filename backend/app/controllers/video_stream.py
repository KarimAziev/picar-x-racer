import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, Optional
import threading
import cv2
import numpy as np
from app.config.logging_config import setup_logger
from app.util.singleton_meta import SingletonMeta

logger = setup_logger(__name__)

# Constants for target width and height of video streams
TARGET_WIDTH = 640
TARGET_HEIGHT = 480


class VideoStreamManager(metaclass=SingletonMeta):
    def __init__(self, max_workers=4, target_fps=60):
        self.max_workers = max_workers
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
        self.lock = threading.Lock()

    def recreate_executor(self):
        if self.executor_shutdown:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self.executor_shutdown = False

    def convert_listproxy_to_array(self, listproxy_obj):
        if listproxy_obj is None:
            logger.error("ListProxy object is None")
            raise ValueError("ListProxy object is None")
        np_array = np.array(listproxy_obj, dtype=np.uint8)
        return np_array

    def get_frame(self) -> bytes:
        with self.lock:
            frame_array = self.flask_img.copy() if self.flask_img is not None else None

        if frame_array is None:
            logger.error("Flask image is None, cannot get frame.")
            raise ValueError("Flask image is None")

        _, buffer = cv2.imencode(".jpg", frame_array)
        return buffer.tobytes()

    def get_png_frame(self) -> bytes:
        with self.lock:
            frame_array = self.flask_img.copy() if self.flask_img is not None else None

        if frame_array is None:
            logger.error("Flask image is None, cannot get frame.")
            raise ValueError("Flask image is None")

        _, buffer = cv2.imencode(".png", frame_array)
        return buffer.tobytes()

    def resize_and_encode(
        self, frame: np.ndarray, width: int, height: int, format=".jpg", quality=90
    ):
        resized_frame = cv2.resize(
            frame, (width, height), interpolation=cv2.INTER_CUBIC
        )
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality] if format == ".jpg" else []
        _, buffer = cv2.imencode(format, resized_frame, encode_params)
        return buffer.tobytes()

    def encode(self, frame_array: np.ndarray, format=".jpg"):
        _, buffer = cv2.imencode(format, frame_array)
        return buffer.tobytes()

    def async_generate_video_stream(
        self, width: int, height: int, format=".jpg", quality=90
    ):
        self.active_clients += 1
        logger.info(f"Active Clients: {self.active_clients}")

        try:
            while True:
                with self.lock:
                    img_copy = (
                        self.flask_img.copy() if self.flask_img is not None else None
                    )

                if img_copy is not None:
                    if self.executor_shutdown:
                        logger.warning(
                            "Executor already shutdown, cannot submit new task."
                        )
                        break
                    future = self.executor.submit(
                        self.resize_and_encode, img_copy, width, height, format, quality
                    )
                    encoded_frame = future.result()
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_frame + b"\r\n"
                else:
                    logger.warning("Flask image is None, skipping frame.")
        finally:
            self.active_clients -= 1
            logger.info(f"Active Clients: {self.active_clients}")
            if self.active_clients == 0 and not self.executor_shutdown:
                self.executor.shutdown(wait=True, cancel_futures=True)
                self.executor_shutdown = True
                logger.info("Executor shut down due to no active clients.")
                self.camera_close()  # Close the camera when no active clients

    def async_generate_video_stream_no_transform(self, format=".png"):
        self.active_clients += 1
        logger.info(f"Active Clients: {self.active_clients}")

        try:
            while True:
                with self.lock:
                    img_copy = (
                        self.flask_img.copy() if self.flask_img is not None else None
                    )

                if img_copy is not None:
                    if self.executor_shutdown:
                        logger.warning(
                            "Executor already shutdown, cannot submit new task."
                        )
                        break
                    future = self.executor.submit(self.encode, img_copy, format)
                    encoded_frame = future.result()
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_frame + b"\r\n"
                else:
                    logger.warning("Flask image is None, skipping frame.")
        finally:
            self.active_clients -= 1
            logger.info(f"Active Clients: {self.active_clients}")
            if self.active_clients == 0 and not self.executor_shutdown:
                self.executor.shutdown(wait=True, cancel_futures=True)
                self.executor_shutdown = True
                logger.info("Executor shut down due to no active clients.")
                self.camera_close()  # Close the camera when no active clients

    def generate_high_quality_stream(self) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream(TARGET_WIDTH, TARGET_HEIGHT)

    def generate_medium_quality_stream(self) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream_no_transform(".jpg")

    def generate_low_quality_stream(self) -> Generator[bytes, None, None]:
        return self.async_generate_video_stream_no_transform(".png")

    def camera_thread_func(self):
        logger.info("Starting camera loop")
        cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            cap.release()
            logger.error(f"Failed to open camera at {self.camera_index}.")
            return

        cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        try:
            while self.camera_run:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame from camera.")
                    continue

                if self.camera_vflip:
                    frame = cv2.flip(frame, 0)
                if self.camera_hflip:
                    frame = cv2.flip(frame, 1)

                with self.lock:
                    self.flask_img = frame.copy()

        except Exception as e:
            logger.error(f"Exception occurred in camera loop: {e}")
        finally:
            cap.release()
            with self.lock:
                self.flask_img = None
            logger.info("Camera loop terminated and camera released.")

    def camera_start(self, vflip=False, hflip=False, fps=60):
        logger.info(f"Starting camera with vflip={vflip}, hflip={hflip}, fps={fps}")
        self.camera_hflip = hflip
        self.camera_vflip = vflip
        self.target_fps = fps
        self.camera_run = True

        self.camera_thread = threading.Thread(target=self.camera_thread_func)
        self.camera_thread.start()

    def camera_close(self):
        logger.info("Closing camera")
        self.camera_run = False
        if hasattr(self, "camera_thread"):
            self.camera_thread.join()
        with self.lock:
            self.flask_img = None

    async def start_camera_and_wait_for_flask_img(
        self, vflip=False, hflip=False, fps=30
    ):
        if not self.camera_run:
            self.camera_start(vflip, hflip, fps)

        while True:
            with self.lock:
                if self.flask_img is not None:
                    break
            logger.info("waiting for flask img")
            await asyncio.sleep(0.1)

    async def take_photo(self, photo_name: str, path: str) -> bool:
        logger.info(f"Taking photo '{photo_name}' at path {path}")
        if not os.path.exists(path):
            os.makedirs(name=path, mode=0o751, exist_ok=True)
            await asyncio.sleep(0.01)

        status = False
        for _ in range(5):
            with self.lock:
                img_copy = self.img.copy() if self.img is not None else None

            if img_copy is not None:
                status = cv2.imwrite(os.path.join(path, photo_name + ".jpg"), img_copy)
                break
            else:
                await asyncio.sleep(0.01)
        else:
            status = False

        return status