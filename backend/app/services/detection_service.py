import asyncio
import multiprocessing as mp
import queue
import re
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.exceptions.detection import (
    DetectionModelLoadError,
    DetectionProcessClosing,
    DetectionProcessError,
    DetectionProcessLoading,
)
from app.schemas.detection import DetectionSettings
from app.util.detection_process import detection_process_func
from app.util.file_util import resolve_absolute_path
from app.util.logger import Logger
from app.util.queue_helpers import clear_queue
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
        self.file_manager = file_manager
        self.connection_manager = connection_manager

        self.detection_settings = DetectionSettings(
            **self.file_manager.settings.get("detection", {})
        )
        self.task_event = asyncio.Event()
        self.stop_event = mp.Event()
        self.frame_queue = mp.Queue(maxsize=1)
        self.detection_queue = mp.Queue(maxsize=1)
        self.control_queue = mp.Queue(maxsize=1)
        self.out_queue = mp.Queue(maxsize=1)
        self.detection_process = None
        self.detection_result: Optional[Dict[str, Any]] = None
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

        if self.shutting_down:
            raise DetectionProcessClosing("Detection process is loading!")
        elif self.loading:
            raise DetectionProcessLoading("Detection process is about to close!")

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
            old_value = detection_data.get(key)
            if old_value != value:
                logger.info(
                    "Updating detection setting '%s': '%s'->'%s'", key, old_value, value
                )
                if key == "active" and value is not None:
                    detection_action = value
                elif key in runtime_data_keys:
                    runtime_data[key] = value
                elif key in detection_keys_to_restart and detection_action is None:
                    detection_action = settings.active

        if detection_action is not None:
            await self.cancel_detection_watcher()
            logger.info("Stopping detection process due to updated settings.")
            await self.stop_detection_process()
        else:
            logger.info("Skipping cancellation of detection process and watcher")

        self.detection_settings = settings

        if detection_action == True:
            await self.start_detection_process()
            if not self.shutting_down:
                self.detection_process_task = asyncio.create_task(
                    self.detection_watcher()
                )
        elif (
            not self.shutting_down
            and detection_action is None
            and len(runtime_data.items()) > 0
        ):
            async with self.lock:
                if (
                    self.detection_process is not None
                    and self.detection_process.is_alive()
                    and hasattr(self, "control_queue")
                ):
                    await asyncio.to_thread(
                        self.clear_and_put,
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
                    raise DetectionModelLoadError("No model, skipping starting process")
                if (
                    self.detection_process is None
                    or not self.detection_process.is_alive()
                ):
                    self.loading = True

                    self.detection_process = mp.Process(
                        target=detection_process_func,
                        args=(
                            resolve_absolute_path(
                                self.detection_settings.model,
                                self.file_manager.data_dir,
                            ),
                            self.stop_event,
                            self.frame_queue,
                            self.detection_queue,
                            self.control_queue,
                            self.out_queue,
                        ),
                    )
                    self.detection_process.start()
                    logger.info("Detection process has been started")
                else:
                    logger.info("Skipping starting of detection process: already alive")

                command = {
                    "command": "set_detect_mode",
                    "confidence": self.detection_settings.confidence,
                    "labels": self.detection_settings.labels,
                }
                logger.info("Waiting for model %s", self.detection_settings.model)
                await self.connection_manager.info(
                    f"Loading model {self.detection_settings.model}"
                )
                msg = await asyncio.to_thread(self.out_queue.get)
                logger.info("Received %s", msg)
                err_msg = msg.get('error')
                if err_msg is not None:
                    raise DetectionModelLoadError(
                        err_msg
                        if isinstance(err_msg, str)
                        else f"Model {self.detection_settings.model} failed to load."
                    )

                await asyncio.to_thread(self.clear_and_put, self.control_queue, command)
                msg = f"Detection is running with {self.detection_settings.model}"
                await self.connection_manager.info(msg)
                logger.info(msg)
        except (
            BrokenPipeError,
            EOFError,
            ConnectionResetError,
            ConnectionError,
            ConnectionRefusedError,
        ) as e:
            logger.warning("Failed to start detection process %s", e)
            await self.connection_manager.error(str(e))
            raise
        except DetectionModelLoadError as e:
            self.detection_settings.active = False
            await self.connection_manager.error(str(e))
            raise
        except Exception as e:
            logger.error(f"Unhandled exception in detection process", exc_info=True)
            await self.connection_manager.error(f"Detection process error: {str(e)}")
            raise
        finally:
            self.loading = False

    async def stop_detection_process(self, clear_queues=True) -> None:
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
                logger.info("Detection process is None, skipping stop")
            else:
                await self.connection_manager.info("Stopping detection process")
                self.stop_event.set()

                logger.info("Detection process setted stop_event")
                await asyncio.to_thread(self.detection_process.join, 10)
                logger.info("Detection process has been joined")
                if self.detection_process.is_alive():
                    logger.warning(
                        "Force terminating detection process since it's still alive."
                    )
                    self.detection_process.terminate()
                    await asyncio.to_thread(self.detection_process.join, 5)
                    self.detection_process.close()
            if clear_queues:
                await asyncio.to_thread(self._cleanup_queues)
            logger.info("Clearing stop event")
            self.stop_event.clear()
            logger.info("Stop event cleared")

            self.detection_result = None
            self.shutting_down = False

            if self.detection_process:
                self.detection_process = None
                logger.info("Detection process has been stopped successfully.")

    async def detection_watcher(self) -> None:
        """
        Background task that monitors the output from the detection process in real-time.

        Behavior:
            - Reads messages from the `out_queue` and handles errors if they arise.
            - Runs continuously until the associated events signal a stop.
        """
        try:
            while (
                hasattr(self, "out_queue")
                and not self.shutting_down
                and not self.task_event.is_set()
                and not self.stop_event.is_set()
            ):

                try:
                    msg = await asyncio.to_thread(self.out_queue.get, timeout=1)
                    logger.debug("msg %s", msg)
                    err = msg.get('error')
                    if err is not None:
                        raise DetectionProcessError(err)
                except queue.Empty:
                    pass
                await asyncio.sleep(1)
        except (
            BrokenPipeError,
            EOFError,
            ConnectionResetError,
            ConnectionError,
            ConnectionRefusedError,
        ) as e:
            self.detection_settings.active = False
            logger.warning(
                "Connection-related error occurred in detection watcher."
                "Exception handled: %s",
                type(e).__name__,
            )
        except DetectionProcessError as e:
            # handling "Cannot set tensor: Dimension mismatch. Got 320 but expected 256 for dimension 1 of input 0."
            pattern = (
                r"Dimension mismatch\. Got (\d+) but expected (\d+) for dimension 1"
            )
            unsupported_pattern = (
                r"Dimension mismatch\. Got (\d+) but expected (\d+) for dimension 2"
            )
            error_message = str(e)
            match = re.search(pattern, error_message)
            got = int(match.group(1)) if match else None
            expected = int(match.group(2)) if match else None
            if (
                match
                and got
                and expected
                and not self.loading
                and not self.shutting_down
                and self.detection_settings.active
                and self.detection_settings.img_size == got
                and self.detection_settings.img_size != expected
            ):
                next_settings = {
                    **self.detection_settings.model_dump(),
                    "img_size": expected,
                }
                self.loading = True
                logger.warning("Dimension mismatch: %s, retrying", error_message)
                await self.stop_detection_process()
                self.detection_settings = DetectionSettings(**next_settings)
                detection_start_task = asyncio.create_task(
                    self.start_detection_process()
                )
                info_task = asyncio.create_task(
                    self.connection_manager.broadcast_json(
                        {
                            "type": "detection",
                            "payload": next_settings,
                            "message": {
                                "text": f"Dimension mismatch: Got {got} but expected {expected}. Retrying with {expected} size.",
                                "type": "warning",
                            },
                        }
                    )
                )

                await asyncio.gather(info_task, detection_start_task)
                self.detection_process_task = asyncio.create_task(
                    self.detection_watcher()
                )

            else:
                self.detection_settings.active = False
                logger.error("Detection process error: %s", error_message)
                err = (
                    error_message
                    if not re.search(unsupported_pattern, error_message)
                    else "The model expects different widths and heights, which is unsupported."
                )
                await self.connection_manager.broadcast_json(
                    {
                        "type": "detection",
                        "payload": self.detection_settings.model_dump(),
                        "message": {"type": "error", "text": err},
                    }
                )

    async def cancel_detection_watcher(self) -> None:
        """
        Cancels the background asyncio detection process task, ensuring it shuts down cleanly.

        Behavior:
            - Signals the task to stop.
            - Handles cancellation gracefully while clearing necessary state.
        """

        if self.detection_process_task:
            logger.info("Cancelling detection task")
            try:
                self.task_event.set()
                self.detection_process_task.cancel()
                await self.detection_process_task
            except asyncio.CancelledError:
                self.detection_process_task = None
                logger.info("Detection task is cancelled")
            finally:
                self.task_event.clear()
        else:
            logger.info("Skipping cancelling detection task")

    def _cleanup_queues(self) -> None:
        """
        Cleans up all multiprocessing queues by clearing their contents.

        Behavior:
            - Ensures safe shutdown of the queues without leaving residual data.
        """
        try:
            for queue_item in [
                self.frame_queue,
                self.control_queue,
                self.detection_queue,
                self.out_queue,
            ]:
                clear_queue(queue_item, reraise=True)
        except (
            ConnectionError,
            ConnectionRefusedError,
            BrokenPipeError,
            EOFError,
            ConnectionResetError,
        ) as e:
            logger.warning(
                "Connection-related error occurred while clearing detection queues."
                "Exception handled: %s",
                type(e).__name__,
            )

    def _close_queues(self) -> None:
        """
        Closes and joins threads for all multiprocessing queues to ensure proper
        cleanup and prevent resource leaks.
        """
        for name in [
            "control_queue",
            "detection_queue",
            "out_queue",
            "frame_queue",
        ]:
            try:
                queue_item: Optional['mp.Queue'] = getattr(self, name, None)
                if not queue_item:
                    continue
                if not queue_item.empty():
                    logger.info(f"Cleaning non empty queue {name}")
                    queue_item.get_nowait()

                logger.info("Closing %s", name)
                queue_item.close()
                logger.info("Joining %s", name)
                queue_item.join_thread()
            except (
                ConnectionError,
                ConnectionRefusedError,
                BrokenPipeError,
                EOFError,
                ConnectionResetError,
            ) as e:
                logger.warning(
                    "Connection-related error occurred while clearing detection queues."
                    "Exception handled: %s",
                    type(e).__name__,
                )

    def put_frame(self, frame_data: Dict[str, Any]) -> None:
        """Puts the frame data into the frame queue after clearing it."""
        if self.shutting_down:
            logger.warning(
                "Skipping putting a frame to detection queue: service is shutting down."
            )
            return None
        if self.loading:
            logger.warning(
                "Skipping putting a frame to detection queue: service is loading."
            )
            return None
        return self.clear_and_put(self.frame_queue, frame_data)

    def clear_and_put(
        self,
        qitem: Optional["mp.Queue"],
        item,
    ):

        if qitem is None:
            return None

        try:
            while not self.shutting_down and qitem and not qitem.empty():
                try:
                    qitem.get_nowait()
                    if self.shutting_down:
                        break
                except queue.Empty:
                    pass
        except (
            ConnectionError,
            ConnectionRefusedError,
            BrokenPipeError,
            EOFError,
            ConnectionResetError,
        ) as e:
            logger.warning(
                "Failed to clear the queue to connection error: %s",
                type(e).__name__,
            )
            return

        if self.shutting_down:
            return
        try:
            qitem.put_nowait(item)
            return item

        except queue.Full:
            pass
        except (
            ConnectionError,
            ConnectionRefusedError,
            BrokenPipeError,
            EOFError,
            ConnectionResetError,
        ) as e:
            logger.warning(
                "Failed to put data into the queue due to a connection-related issue: %s",
                type(e).__name__,
            )

    @property
    def current_state(self):
        """
        Retrieves the current state of the detection service, including the latest detection results.

        Returns:
            The current state with keys:
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
            - Deletes class properties associated with multiprocessing and async state.
        """
        self.shutting_down = True
        await self.cancel_detection_watcher()
        await self.stop_detection_process(clear_queues=False)

        self._close_queues()

        for prop in [
            "stop_event",
            "frame_queue",
            "control_queue",
            "detection_queue",
            "out_queue",
            "detection_process",
        ]:
            if hasattr(self, prop):
                logger.info(f"Removing {prop}")
                delattr(self, prop)
