import json
import multiprocessing as mp
import queue
import threading
import time
from typing import TYPE_CHECKING, Optional

from app.config.paths import DATA_DIR, YOLO_MODEL_PATH
from app.services.client_notifier import ClientNotifier
from app.util.detection_process import detection_process_func
from app.util.file_util import resolve_absolute_path
from app.util.google_coral import is_google_coral_connected
from app.util.logger import Logger
from app.util.queue import clear_and_put, clear_queue
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket

if TYPE_CHECKING:
    from app.services.files_service import FilesService

logger = Logger(__name__)


class DetectionService(ClientNotifier, metaclass=SingletonMeta):
    def __init__(self, file_manager: "FilesService"):
        self.lock = threading.Lock()
        self.logger = Logger(__name__)
        self.file_manager = file_manager
        self.stop_event = mp.Event()
        self.manager = mp.Manager()
        self.frame_queue = self.manager.Queue(maxsize=1)
        self.detection_queue = self.manager.Queue(maxsize=1)
        self.control_queue = self.manager.Queue(maxsize=2)
        self.out_queue = self.manager.Queue(maxsize=1)
        self.detection_process = None
        self.detection_result = None
        self.active_connections: list[WebSocket] = []
        self.loading = False
        self._video_feed_confidence = self.file_manager.settings.get(
            "video_feed_confidence", 0.3
        )
        self._video_feed_detect_mode: Optional[str] = self.file_manager.settings.get(
            "video_feed_detect_mode", YOLO_MODEL_PATH
        )

        self.video_feed_object_detection = self.file_manager.settings.get(
            "video_feed_object_detection", False
        )

    @staticmethod
    def check_model(model: Optional[str]):
        if model is None:
            return None
        if model.endswith(".tflite") and not is_google_coral_connected():
            next_model = resolve_absolute_path(YOLO_MODEL_PATH, DATA_DIR)
            logger.warning(
                "Google coral is not connected, setting model to %s", next_model
            )
            return next_model
        else:
            return model

    def start_detection_process(self):
        with self.lock:
            if self.video_feed_detect_mode is None:
                return
            if self.detection_process is None or not self.detection_process.is_alive():
                self.loading = True
                self.detection_process = mp.Process(
                    target=detection_process_func,
                    args=(
                        resolve_absolute_path(self.video_feed_detect_mode, DATA_DIR),
                        self.stop_event,
                        self.frame_queue,
                        self.detection_queue,
                        self.control_queue,
                        self.out_queue,
                    ),
                )
                self.detection_process.start()
                self.logger.info("Detection process has been started")
            else:
                self.logger.info(
                    "Skipping starting of detection process: already alive"
                )

            command = {
                "command": "set_detect_mode",
                "confidence": self.video_feed_confidence,
            }

            try:
                self.logger.info("Waiting for loading model")
                msg = self.out_queue.get()
                self.logger.info("Received %s", msg)
                clear_and_put(self.control_queue, command)
                self.logger.info("Command putted")
            except Exception:
                self.logger.log_exception("Exception occurred")
            finally:
                self.loading = False

    def stop_detection_process(self):
        with self.lock:
            if self.detection_process is None:
                self.logger.info("Detection process is None, skipping stop")
            else:
                self.stop_event.set()

                self.logger.info("Detection process setted stop_event")
                self.detection_process.join(timeout=10)
                self.logger.info("Detection process has been joined")
                if self.detection_process.is_alive():
                    self.logger.warning(
                        "Force terminating detection process since it's still alive."
                    )
                    self.detection_process.terminate()
                    self.detection_process.join(timeout=5)
                    self.detection_process.close()

            self._cleanup_queues()
            self.clear_stop_event()

            if self.detection_process:
                self.detection_process = None

            self.logger.info("Detection process has been stopped successfully.")

    def _cleanup_queues(self):
        """Empty queues or safely close them before shutdown."""
        for queue_item in [
            self.frame_queue,
            self.control_queue,
            self.detection_queue,
            self.out_queue,
        ]:
            clear_queue(queue_item)

    def clear_stop_event(self):
        self.logger.info("Clearing stop event")
        self.stop_event.clear()
        self.logger.info("Stop event cleared")

    def restart_detection_process(self):
        self.stop_detection_process()
        self.start_detection_process()
        self.logger.info("Detection process has been restarted")

    def put_frame(self, frame_data):
        """Puts the frame data into the frame queue after clearing it."""
        return clear_and_put(self.frame_queue, frame_data)

    def put_command(self, command_data):
        """Puts the control queue into the frame queue after clearing it."""
        return clear_and_put(self.control_queue, command_data)

    @property
    def video_feed_confidence(self):
        return self._video_feed_confidence

    @video_feed_confidence.setter
    def video_feed_confidence(self, new_confidence):
        if self._video_feed_confidence != new_confidence:
            self._video_feed_confidence = new_confidence
            if hasattr(self, "control_queue"):
                try:
                    clear_and_put(
                        self.control_queue,
                        {
                            "command": "set_detect_mode",
                            "confidence": new_confidence,
                        },
                    )
                except Exception as e:
                    self.logger.log_exception("Unexpected error", e)

    @property
    def video_feed_detect_mode(self):
        """
        Gets the current video feed detection mode.

        Returns:
            Optional[str]: The current detection mode (e.g., 'cat', 'person', 'all'),
            or None if detection is disabled.
        """

        return self._video_feed_detect_mode

    @video_feed_detect_mode.setter
    def video_feed_detect_mode(self, new_mode):
        """
        Sets the video feed detection mode and communicates the change to the detection process.

        Args:
            new_mode (Optional[str]): The new detection mode to set. If None, detection is disabled.
        """

        self.logger.info(f"Setting video_feed_detect_mode to {new_mode}")
        self._video_feed_detect_mode = DetectionService.check_model(new_mode)
        if self.video_feed_object_detection:
            self.stop_detection_process()
            self.start_detection_process()

    async def handle_notify_client(self, websocket: WebSocket):
        data = (
            self.detection_result
            if self.detection_result is not None
            else {"detection_result": [], "timestamp": time.time()}
        )

        await websocket.send_text(
            json.dumps(
                {**data, "model": self.video_feed_detect_mode, "loading": self.loading}
            )
        )

    def cleanup(self):
        self.stop_detection_process()
        if self.manager is not None:
            logger.info("Shutdown detection manager")
            self.manager.shutdown()
            logger.info("Detection manager has been shutdown")
            self.manager.join()
        for prop in [
            "stop_event",
            "frame_queue",
            "control_queue",
            "detection_queue",
            "out_queue",
            "detection_process",
            "manager",
        ]:
            if hasattr(self, prop):
                logger.info(f"Removing {prop}")
                delattr(self, prop)

    def get_detection(self):
        if self.stop_event.is_set():
            return None
        try:
            self.logger.debug("Waiting for detection_result")
            self.detection_result = self.detection_queue.get(timeout=1)
        except queue.Empty:
            self.detection_result = None

        return self.detection_result
