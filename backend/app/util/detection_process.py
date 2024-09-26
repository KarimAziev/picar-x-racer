import multiprocessing as mp
import queue
from multiprocessing.synchronize import Event

from app.config.detectors import detectors
from app.util.logger import Logger
from app.util.model_manager import ModelManager
from app.util.print_memory_usage import print_memory_usage

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

    print_memory_usage("Memory Usage Before Loading the Model")
    with ModelManager() as yolo_model:
        try:
            logger.info(f"YOLO yolo_model.task {yolo_model.task}")
            current_detect_mode = None
            detection_function = None
            counter = 0

            while not stop_event.is_set():
                try:
                    try:
                        while not control_queue.empty():
                            control_message = control_queue.get_nowait()
                            if control_message.get("command") == "set_detect_mode":
                                current_detect_mode = control_message.get("mode")
                                logger.info(
                                    f"current_detect_mode: {current_detect_mode}"
                                )
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
                        frame = frame_queue.get(timeout=1)
                    except queue.Empty:
                        continue

                    detection_result = detection_function(
                        frame=frame, yolo_model=yolo_model
                    )
                    if detection_result and counter < 5:
                        logger.debug(f"Detection result: {detection_result}")
                        counter += 1

                    try:
                        detection_queue.put_nowait(detection_result)
                    except queue.Full:
                        pass

                except Exception as e:
                    logger.error(f"Error in detection_process_func: {e}")
        except KeyboardInterrupt:
            logger.info("Detection process received KeyboardInterrupt, exiting.")
        finally:
            logger.info("Detection process is terminating.")

        print_memory_usage("Memory Usage After Loading the Model")

    print_memory_usage("Memory Usage After Deleting the Model")
