import multiprocessing as mp
import queue
from typing import TYPE_CHECKING, Optional

from app.util.detection_process import detection_process_func
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from app.services.files_service import FilesService


class DetectionService(metaclass=SingletonMeta):
    def __init__(self, file_manager: "FilesService"):
        self.logger = Logger(__name__)
        self.stop_event = mp.Event()
        self.manager = mp.Manager()
        self.file_manager = file_manager
        self.frame_queue = self.manager.Queue(maxsize=1)
        self.detection_queue = self.manager.Queue(maxsize=1)
        self.control_queue = self.manager.Queue(maxsize=2)
        self.detection_process = None
        self._video_feed_confidence = self.file_manager.settings.get(
            "video_feed_confidence", 0.3
        )
        self._video_feed_detect_mode: Optional[str] = self.file_manager.settings.get(
            "video_feed_detect_mode"
        )

    def start_detection_process(self):
        if not self.detection_process or not self.detection_process.is_alive():
            self.detection_process = mp.Process(
                target=detection_process_func,
                args=(
                    self.stop_event,
                    self.frame_queue,
                    self.detection_queue,
                    self.control_queue,
                ),
                daemon=True,
            )
            self.detection_process.start()
            self.logger.info("Detection process has been started")
        else:
            self.logger.info("Skipping starting of detection process: already alive")

        command = {
            "command": "set_detect_mode",
            "mode": self.video_feed_detect_mode,
            "confidence": self.video_feed_confidence,
        }

        try:
            self.put_command(command)
        except BrokenPipeError as e:
            self.logger.log_exception(f"BrokenPipeError", e)
        except queue.Full:
            self.logger.error("Queue is full")
        except queue.Empty:
            self.logger.error("Queue is empty")
        except Exception as e:
            self.logger.log_exception(f"BrokenPipeError", e)

    def stop_detection_process(self):
        if self.detection_process is None:
            self.logger.info("Detection process is None, skipping stop")
        elif self.detection_process.is_alive():
            self.stop_event.set()
            self.logger.info("Detection process setted stop_event")
            self.detection_process.join()

            self.logger.info("Detection process has been stopped")
        else:
            self.logger.info("Detection process is not alive")

    def clear_stop_event(self):
        self.logger.info("Clearing stop event")
        self.stop_event.clear()
        self.logger.info("Stop event cleared")

    def restart_detection_process(self):
        self.stop_detection_process()
        self.clear_stop_event()
        self.start_detection_process()
        self.logger.info("Detection process has been restarted")

    def clear_frame_queue(self):
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass

    def put_frame(self, frame_data):
        """Puts the frame data into the frame queue after clearing it."""
        self.clear_frame_queue()
        try:
            self.frame_queue.put_nowait(frame_data)
        except queue.Full:
            pass

    def get_detection_result(self):
        """Retrieves the latest detection result from the detection queue."""
        try:
            return self.detection_queue.get_nowait()
        except queue.Empty:
            return None

    def clear_control_queue(self):
        while not self.control_queue.empty():
            try:
                self.control_queue.get_nowait()
            except queue.Empty:
                pass

    def put_command(self, command_data):
        """Puts the control queue into the frame queue after clearing it."""
        self.clear_control_queue()
        try:
            self.control_queue.put_nowait(command_data)
        except queue.Full:
            pass

    @property
    def video_feed_confidence(self):
        return self._video_feed_confidence

    @video_feed_confidence.setter
    def video_feed_confidence(self, new_confidence):
        if self._video_feed_confidence != new_confidence:
            self._video_feed_confidence = new_confidence
            if hasattr(self, "control_queue"):

                command = {
                    "command": "set_detect_mode",
                    "mode": self.video_feed_detect_mode,
                    "confidence": new_confidence,
                }
                try:
                    self.put_command(command)
                except BrokenPipeError as e:
                    self.logger.log_exception("BrokenPipeError", e)
                except queue.Full:
                    self.logger.error("Queue is full")
                except queue.Empty:
                    self.logger.error("Queue is empty")
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
        self._video_feed_detect_mode = new_mode
        if hasattr(self, "control_queue"):

            command = {
                "command": "set_detect_mode",
                "mode": new_mode,
                "confidence": self.video_feed_confidence,
            }
            try:
                self.put_command(command)
            except BrokenPipeError as e:
                self.logger.log_exception("BrokenPipeError", e)
            except queue.Full:
                self.logger.error("Queue is full")
            except queue.Empty:
                self.logger.error("Queue is empty")
            except Exception as e:
                self.logger.log_exception("Unexpected error", e)
