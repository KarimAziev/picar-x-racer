import asyncio
import multiprocessing as mp
import queue
import time
from typing import TYPE_CHECKING, Optional

from app.config.paths import DATA_DIR
from app.exceptions.detection import DetectionModelLoadError, DetectionProcessError
from app.schemas.detection import DetectionSettings
from app.util.detection_process import detection_process_func
from app.util.file_util import resolve_absolute_path
from app.util.logger import Logger
from app.util.queue import clear_and_put, clear_queue
from app.util.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.file_service import FileService

logger = Logger(__name__)


class DetectionService(metaclass=SingletonMeta):
    """
    A service class for managing object detection processes. This service handles
    starting, stopping, and updating settings for object detection using multiprocessing
    and asynchronous tasks.
    """

    def __init__(
        self, file_manager: "FileService", connection_manager: "ConnectionService"
    ):
        self.lock = asyncio.Lock()
        self.logger = Logger(__name__)
        self.file_manager = file_manager
        self.connection_manager = connection_manager

        self.detection_settings = DetectionSettings(
            **self.file_manager.settings.get("detection", {})
        )
        self.task_event = asyncio.Event()
        self.stop_event = mp.Event()
        self.manager = mp.Manager()
        self.frame_queue = self.manager.Queue(maxsize=1)
        self.detection_queue = self.manager.Queue(maxsize=1)
        self.control_queue = self.manager.Queue(maxsize=2)
        self.out_queue = self.manager.Queue(maxsize=1)
        self.detection_process = None
        self.detection_result = None
        self.detection_process_task: Optional[asyncio.Task] = None
        self.loading = False
        self.shutting_down = False

    async def update_detection_settings(
        self, settings: DetectionSettings
    ) -> DetectionSettings:
        """
        Updates the detection settings and applies the changes to the detection process.

        Args:
            settings (DetectionSettings): The new detection configuration.

        Behavior:
            - Compares the new settings with the existing ones.
            - Restarts the detection process if required by updates in critical settings.
            - Dynamically updates runtime settings like confidence and labels without restarting.

        Returns:
            DetectionSettings: The updated detection settings.
        """
        detection_action = None
        dict_data = settings.model_dump()
        detection_data = self.detection_settings.model_dump(exclude_unset=True)
        detection_keys_to_restart = {
            "img_size",
            "model",
        }

        runtime_data_keys = {"confidence", "labels"}

        runtime_data = {}

        for key, value in dict_data.items():
            if detection_data.get(key) != value:
                self.logger.info("updating %s: %s", key, value)
                if key == "active" and value is not None:
                    detection_action = value
                elif key in runtime_data_keys:
                    runtime_data[key] = value
                elif key in detection_keys_to_restart and detection_action is None:
                    detection_action = settings.active

        if detection_action is not None:
            await self.cancel_detection_process_task()
            await self.stop_detection_process()

        self.detection_settings = settings

        if detection_action == True:
            await self.start_detection_process()
            self.detection_process_task = asyncio.create_task(
                self.start_detection_process_task()
            )
        elif detection_action is None and len(runtime_data.items()) > 0:
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

    async def start_detection_process(self) -> None:
        """
        Starts the detection process as a multiprocessing subprocess.

        Behavior:
            - Ensures the model is loaded and initializes required resources.
            - Configures the detection subprocess and provides the necessary queues.
            - Broadcasts updates to connected clients regarding the operational status.

        Raises:
            DetectionModelLoadError: If the detection model fails to load.
            Exception: For unhandled errors during initialization.
        """
        try:
            async with self.lock:
                if self.detection_settings.model is None:
                    await self.connection_manager.info(
                        f"No model, skipping starting model"
                    )
                    return
                if (
                    self.detection_process is None
                    or not self.detection_process.is_alive()
                ):

                    self.loading = True
                    self.detection_process = mp.Process(
                        target=detection_process_func,
                        args=(
                            resolve_absolute_path(
                                self.detection_settings.model, DATA_DIR
                            ),
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
                self.logger.info(
                    "Waiting for model %s", {self.detection_settings.model}
                )
                await self.connection_manager.info(
                    f"Loading model {self.detection_settings.model}"
                )
                msg = await asyncio.to_thread(self.out_queue.get)
                self.logger.info("Received %s", msg)
                if msg.get('error') is not None:
                    raise DetectionModelLoadError(
                        f"Model {self.detection_settings.model} failed to load"
                    )

                await asyncio.to_thread(clear_and_put, self.control_queue, command)
                msg = f"Detection is running with {self.detection_settings.model}"
                await self.connection_manager.info(msg)
                self.logger.info(msg)
        except DetectionModelLoadError as e:
            await self.connection_manager.error(str(e))
            raise DetectionModelLoadError from e
        except Exception as e:
            self.logger.exception(f"Unhandled exception in detection process: {e}")
            await self.connection_manager.error(f"Detection process error: {str(e)}")
            raise e
        finally:
            self.loading = False

    async def stop_detection_process(self) -> None:
        """
        Stops the currently running detection process.

        Behavior:
            - Signals the process to stop using the `stop_event`.
            - Waits for the process to terminate, forcibly closing it if required.
            - Cleans up shared resources like queues and resets state.
        """
        async with self.lock:
            self.shutting_down = True
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
            self.logger.info("Clearing stop event")
            self.stop_event.clear()
            self.logger.info("Stop event cleared")

            self.detection_result = None
            self.shutting_down = False

            if self.detection_process:
                self.detection_process = None
                self.logger.info("Detection process has been stopped successfully.")

    async def start_detection_process_task(self) -> None:
        """
        Background task that monitors the output from the detection process in real-time.

        Behavior:
            - Reads messages from the `out_queue` and handles errors if they arise.
            - Runs continuously until the associated events signal a stop.
        """
        try:
            while (
                hasattr(self, "out_queue")
                and not self.task_event.is_set()
                and not self.stop_event.is_set()
            ):

                try:
                    msg = await asyncio.to_thread(self.out_queue.get, timeout=1)
                    self.logger.debug("msg %s", msg)
                    err = msg.get('error')
                    if err is not None:
                        raise DetectionProcessError(err)
                except queue.Empty:
                    pass
                await asyncio.sleep(0.5)
        except (BrokenPipeError, EOFError, ConnectionResetError):
            self.detection_settings.active = False
        except DetectionProcessError as e:
            self.detection_settings.active = False
            await self.connection_manager.broadcast_json(
                {"type": "detection", "payload": self.detection_settings.model_dump()}
            )
            await self.connection_manager.error(f"Detection process error: {e}")

    async def cancel_detection_process_task(self) -> None:
        """
        Cancels the background asyncio detection process task, ensuring it shuts down cleanly.

        Behavior:
            - Signals the task to stop.
            - Handles cancellation gracefully while clearing necessary state.
        """

        if self.detection_process_task:
            self.logger.info("Cancelling detection task")
            try:
                self.task_event.set()

                self.detection_process_task.cancel()
                await self.detection_process_task
            except asyncio.CancelledError:
                self.logger.info("Detection task is cancelled")
                self.detection_process_task = None
            finally:
                self.task_event.clear()

    def _cleanup_queues(self) -> None:
        """
        Cleans up all multiprocessing queues by clearing their contents.

        Behavior:
            - Ensures safe shutdown of the queues without leaving residual data.
        """
        for queue_item in [
            self.frame_queue,
            self.control_queue,
            self.detection_queue,
            self.out_queue,
        ]:
            clear_queue(queue_item)

    def put_frame(self, frame_data) -> None:
        """Puts the frame data into the frame queue after clearing it."""
        if self.shutting_down:
            return None
        return clear_and_put(self.frame_queue, frame_data)

    def put_command(self, command_data) -> None:
        """Puts the control queue into the frame queue after clearing it."""
        return clear_and_put(self.control_queue, command_data)

    @property
    def current_state(self):
        """
        Retrieves the current state of the detection service, including the latest detection results.

        Returns:
            dict: The current state with keys:
                - `detection_result`: The latest detection results (or an empty result if none exist).
                - `timestamp`: The timestamp associated with the detection results.
                - `loading`: A flag indicating whether a detection load operation is in progress.
        """
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

    async def cleanup(self) -> None:
        """
        Performs cleanup operations for the detection service, preparing it for shutdown.

        Behavior:
            - Cancels any running tasks and stops the detection process.
            - Shuts down the multiprocessing manager.
            - Deletes class properties associated with multiprocessing and async state.
        """
        self.shutting_down = True
        await self.cancel_detection_process_task()
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
        """
        Retrieves the latest detection result from the detection process.

        Returns:
            dict or None: The detection result, or `None` if no result is available.
        """
        if self.shutting_down:
            self.logger.warning(
                "Attempted to get detection while service is shutting down."
            )
            return None
        if self.stop_event.is_set():
            return None
        try:
            self.detection_result = self.detection_queue.get(timeout=1)
        except queue.Empty:
            self.detection_result = None
        except (BrokenPipeError, EOFError, ConnectionResetError):
            self.detection_result = None

        return self.detection_result
