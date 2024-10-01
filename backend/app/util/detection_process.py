import multiprocessing as mp
import queue
from multiprocessing.synchronize import Event

from app.config.detectors import detectors
from app.util.logger import Logger
from app.util.model_manager import ModelManager

logger = Logger(name=__name__)


def detection_process_func(
    stop_event: Event,
    frame_queue: mp.Queue,
    detection_queue: mp.Queue,
    control_queue: mp.Queue,
):
    """
    Function run in a separate process to perform object detection on video frames.

    Args:
        stop_event (mp.Event): Event to signal the process to stop.
        frame_queue (mp.Queue): Queue from which frames are retrieved.
        detection_queue (mp.Queue): Queue to put detection results into.
        control_queue (mp.Queue): Queue for control messages.
    """
    with ModelManager() as yolo_model:
        if yolo_model is None:
            logger.error("Failed to load the YOLO model. Exiting detection process.")
            return
        try:
            current_detect_mode = None
            detection_function = None
            confidence_threshold = 0.3
            counter = 0

            while not stop_event.is_set():
                try:
                    try:
                        while not control_queue.empty():
                            control_message = control_queue.get_nowait()
                            if control_message.get("command") == "set_detect_mode":
                                current_detect_mode = control_message.get("mode")
                                confidence: float = control_message.get("confidence")

                                logger.info(
                                    f"current_detect_mode: {current_detect_mode} confidence: {confidence}"
                                )
                                if confidence:
                                    confidence_threshold = confidence
                                detection_function = (
                                    detectors.get(current_detect_mode)
                                    if current_detect_mode
                                    else None
                                )
                    except queue.Empty:
                        pass

                    if detection_function is None:
                        continue

                    try:
                        frame_data = frame_queue.get(timeout=1)
                        frame = frame_data["frame"]
                        frame_timestamp = frame_data["timestamp"]
                    except queue.Empty:
                        continue

                    verbose = counter < 5

                    detection_result = detection_function(
                        frame=frame,
                        yolo_model=yolo_model,
                        confidence_threshold=confidence_threshold,
                        verbose=verbose,
                    )
                    detection_result_with_timestamp = {
                        "detection_result": detection_result,
                        "timestamp": frame_timestamp,
                    }

                    if detection_result and verbose:
                        logger.debug(f"Detection result: {detection_result}")
                        counter += 1

                    try:
                        detection_queue.put_nowait(detection_result_with_timestamp)
                    except queue.Full:
                        pass

                except Exception as e:
                    logger.log_exception("Error in detection_process_func", e)
        except KeyboardInterrupt:
            logger.warning("Detection process received KeyboardInterrupt, exiting.")
        finally:
            logger.info("Detection process is terminating.")
