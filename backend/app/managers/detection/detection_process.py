import queue
import sys
import time
from typing import TYPE_CHECKING

from app.core.logger import Logger
from app.exceptions.detection import DetectionDimensionMismatch
from app.managers.detection.object_detection import perform_detection
from app.managers.model_manager import ModelManager
from app.util.queue_helpers import put_to_queue

if TYPE_CHECKING:
    import multiprocessing as mp
    from multiprocessing.synchronize import Event

logger = Logger(name=__name__)

verbose_enabled = sys.stdout.isatty()


def detection_process_func(
    model: str,
    stop_event: "Event",
    frame_queue: "mp.Queue",
    detection_queue: "mp.Queue",
    control_queue: "mp.Queue",
    out_queue: "mp.Queue",
):
    """
    A function that runs in a separate multiprocessing process to perform object detection on input frames.

    Args:
        model: Path to the YOLO-based object detection model.
        stop_event: A multiprocessing event used to signal the process to stop.
        frame_queue: A queue from which frames are retrieved for detection.
        detection_queue: A queue where object detection results are placed.
        control_queue: A queue for control commands (e.g., updating confidence thresholds or detection labels).
        out_queue: A queue for sending the detection process's success or error statuses.

    Behavior:
        - Loads the specified YOLO model and initializes required settings.
        - Processes frames from the `frame_queue` and performs object detection.
        - Updates detection settings dynamically using messages from the `control_queue`.
        - Outputs detection results with timestamps to the `detection_queue`.
        - Sends success or error messages to the `out_queue`.
        - Stops gracefully when the `stop_event` is set.
    """
    with ModelManager(model) as pair:
        try:
            yolo_model, err_msg = pair
            if yolo_model is None:
                msg = (
                    err_msg
                    or f"Failed to load the model {model}. Exiting detection process."
                )
                logger.error(msg)
                put_to_queue(out_queue, {"success": False, "error": msg}, reraise=True)
                return
            else:
                put_to_queue(out_queue, {"success": True}, reraise=True)
            confidence_threshold = 0.3
            prev_time = time.time()
            labels = None

            while not stop_event.is_set():
                try:
                    while not control_queue.empty():
                        control_message = control_queue.get_nowait()
                        if control_message.get("command") == "set_detect_mode":
                            confidence: float = control_message.get("confidence")
                            labels = control_message.get("labels")

                            logger.info(f"confidence: {confidence}")
                            if confidence:
                                confidence_threshold = confidence
                except queue.Empty:
                    pass

                try:
                    frame_data = frame_queue.get(timeout=1)
                    frame = frame_data["frame"]
                    frame_timestamp = frame_data["timestamp"]
                except queue.Empty:
                    continue

                curr_time = time.time()
                verbose = verbose_enabled and curr_time - prev_time >= 5

                try:
                    detection_result = perform_detection(
                        frame=frame,
                        yolo_model=yolo_model,
                        confidence_threshold=confidence_threshold,
                        verbose=verbose,
                        original_height=frame_data["original_height"],
                        original_width=frame_data["original_width"],
                        resized_height=frame_data["resized_height"],
                        resized_width=frame_data["resized_width"],
                        should_resize=frame_data["should_resize"],
                        labels_to_detect=labels,
                    )
                except DetectionDimensionMismatch as e:
                    put_to_queue(out_queue, {"error": str(e)}, reraise=True)
                    break
                except Exception as e:
                    logger.error(
                        "Unhandled exception in detection process", exc_info=True
                    )
                    put_to_queue(out_queue, {"error": str(e)}, reraise=True)
                    break

                detection_result_with_timestamp = {
                    "detection_result": detection_result,
                    "timestamp": frame_timestamp,
                }

                if verbose:
                    logger.info(f"Detection result: {detection_result}")
                    prev_time = time.time()

                put_to_queue(
                    detection_queue, detection_result_with_timestamp, reraise=True
                )
        except (
            ConnectionError,
            ConnectionRefusedError,
            BrokenPipeError,
            EOFError,
            ConnectionResetError,
        ) as e:
            logger.warning(
                "Connection-related error occurred in detection process: %s",
                type(e).__name__,
            )
        except KeyboardInterrupt:
            logger.warning("Detection process received keyboard interrupt, exiting.")
            stop_event.set()

        finally:
            logger.info("Detection process is finished.")
