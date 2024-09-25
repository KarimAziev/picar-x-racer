import multiprocessing as mp
import queue
from typing import Optional

from app.util.detection_process import detection_process_func
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta


class DetectionController(metaclass=SingletonMeta):
    def __init__(self):
        self.logger = Logger(__name__)
        self.stop_event = mp.Event()
        self.manager = mp.Manager()
        self.frame_queue = self.manager.Queue()
        self.detection_queue = self.manager.Queue()
        self.control_queue = self.manager.Queue()
        self.detection_process = None
        self._video_feed_detect_mode: Optional[str] = None

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
        }

        try:
            self.control_queue.put_nowait(command)
        except BrokenPipeError as e:
            self.logger.error(f"BrokenPipeError: {e}")
        except queue.Full:
            self.logger.error("Queue is full")
        except queue.Empty:
            self.logger.error("Queue is empty")
        except Exception as e:
            self.logger.log_exception("Unexpected error: %s", e)

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
            command = {"command": "set_detect_mode", "mode": new_mode}
            try:
                self.control_queue.put_nowait(command)
            except BrokenPipeError as e:
                self.logger.error(f"BrokenPipeError: {e}")
            except queue.Full:
                self.logger.error("Queue is full")
            except queue.Empty:
                self.logger.error("Queue is empty")
            except Exception as e:
                self.logger.log_exception("Unexpected error: %s", e)
