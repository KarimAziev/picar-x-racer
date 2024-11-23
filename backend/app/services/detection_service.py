import asyncio
import multiprocessing as mp
import queue
import time
from typing import TYPE_CHECKING, Optional

from app.config.paths import DATA_DIR, YOLO_MODEL_PATH
from app.schemas.detection import DetectionSettings
from app.util.detection_process import detection_process_func
from app.util.file_util import resolve_absolute_path
from app.util.google_coral import is_google_coral_connected
from app.util.logger import Logger
from app.util.queue import clear_and_put, clear_queue
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.files_service import FilesService

logger = Logger(__name__)


class DetectionService(metaclass=SingletonMeta):
    def __init__(
        self, file_manager: "FilesService", connection_manager: "ConnectionService"
    ):
        self.lock = asyncio.Lock()
        self.logger = Logger(__name__)
        self.file_manager = file_manager
        self.connection_manager = connection_manager
        self.detection_settings = DetectionSettings(
            **self.file_manager.settings.get("detection", {})
        )
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

    async def update_detection_settings(self, settings: DetectionSettings):
        detection_action = None
        dict_data = settings.model_dump()
        detection_data = self.detection_settings.model_dump(exclude_unset=True)
        detection_keys_to_restart = {
            "img_size",
            "model",
        }

        runtime_data_keys = {"confidence", "labels"}

        runtime_data = {}
        detection_action = settings.active

        for key, value in dict_data.items():
            if detection_data.get(key) != value:
                self.logger.info("updating %s: %s", key, value)
                if key == "active" and value is not None:
                    detection_action = value
                elif key in runtime_data_keys:
                    runtime_data[key] = value
                elif key in detection_keys_to_restart and detection_action is None:
                    detection_action = True

        if detection_action is not None:
            await self.stop_detection_process()

        self.detection_settings = settings

        if detection_action == True:
            await self.start_detection_process()

        if detection_action is None and len(runtime_data.items()) > 0:
            async with self.lock:
                if (
                    self.detection_process is not None
                    and self.detection_process.is_alive()
                    and hasattr(self, "control_queue")
                ):
                    await asyncio.to_thread(
                        clear_and_put,
                        self.control_queue,
                        {"command": "set_detect_mode", **runtime_data},
                    )

        return self.detection_settings

    async def start_detection_process(self):
        async with self.lock:
            if self.detection_settings.model is None:
                await self.connection_manager.info(f"No model, skipping starting model")
                return
            if self.detection_process is None or not self.detection_process.is_alive():
                self.connection_manager
                self.loading = True
                self.detection_process = mp.Process(
                    target=detection_process_func,
                    args=(
                        resolve_absolute_path(self.detection_settings.model, DATA_DIR),
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
                "confidence": self.detection_settings.confidence,
                "labels": self.detection_settings.labels,
            }

            try:
                self.logger.info("Waiting for loading model")
                await self.connection_manager.info(
                    f"Loading model {self.detection_settings.model}"
                )
                msg = await asyncio.to_thread(self.out_queue.get)
                self.logger.info("Received %s", msg)
                await asyncio.to_thread(clear_and_put, self.control_queue, command)
                await self.connection_manager.info(
                    f"Detection process is started with {self.detection_settings.model}"
                )
                self.logger.info("Detection process is started")
            except Exception:
                self.logger.log_exception("Exception occurred")
            finally:
                self.loading = False

    async def stop_detection_process(self):
        async with self.lock:
            if self.detection_process is None:
                self.logger.info("Detection process is None, skipping stop")
            else:
                await self.connection_manager.info("Stopping detection process")
                self.stop_event.set()

                self.logger.info("Detection process setted stop_event")
                await asyncio.to_thread(self.detection_process.join, 10)
                self.logger.info("Detection process has been joined")
                if self.detection_process.is_alive():
                    self.logger.warning(
                        "Force terminating detection process since it's still alive."
                    )
                    self.detection_process.terminate()
                    await asyncio.to_thread(self.detection_process.join, 5)
                    self.detection_process.close()
            await asyncio.to_thread(self._cleanup_queues)
            self.clear_stop_event()

            self.detection_result = None

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

    async def restart_detection_process(self):
        await self.stop_detection_process()
        await self.start_detection_process()
        self.logger.info("Detection process has been restarted")

    def put_frame(self, frame_data):
        """Puts the frame data into the frame queue after clearing it."""
        return clear_and_put(self.frame_queue, frame_data)

    def put_command(self, command_data):
        """Puts the control queue into the frame queue after clearing it."""
        return clear_and_put(self.control_queue, command_data)

    @property
    def current_state(self):
        data = (
            self.detection_result
            if self.detection_result is not None
            else {
                "detection_result": [],
                "timestamp": time.time(),
            }
        )
        return {
            **data,
            "loading": self.loading,
        }

    async def cleanup(self):
        await self.stop_detection_process()
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
            self.detection_result = self.detection_queue.get(timeout=1)
        except queue.Empty:
            self.detection_result = None

        return self.detection_result
