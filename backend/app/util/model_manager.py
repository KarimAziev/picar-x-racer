import gc
import os

from app.config.paths import DATA_DIR, YOLO_MODEL_EDGE_TPU_PATH, YOLO_MODEL_PATH
from app.util.file_util import resolve_absolute_path
from app.util.google_coral import is_google_coral_connected
from app.util.logger import Logger

logger = Logger(__name__)


class ModelManager:
    """
    ModelManager class is a context manager used for loading and managing the lifecycle of a YOLO object detection model.

    This class ensures that the model is loaded when entering the context and properly cleaned up upon exiting the context.
    The model loading path is selected dynamically based on available files.
    """

    def __init__(self, model_path=None):
        """
        Initializes the ModelManager with an optional model path.

        Parameters:
            model_path (str): An optional custom path to use for loading the model.
        """
        self.model = None
        self.model_path = (
            resolve_absolute_path(model_path, DATA_DIR)
            if model_path is not None
            else model_path
        )

    def __enter__(self):
        """
        Called when entering the context (i.e. using the 'with' statement).
        Tries to load the YOLO object detection model from the model paths defined in configuration.

        - If a pre-compiled model for Google's Coral Edge TPU exists (`YOLO_MODEL_EDGE_TPU_PATH`),
          it is loaded.
        - Otherwise, the default YOLO model from `YOLO_MODEL_PATH` is loaded.

        The method also sets an image input size configuration for the model.

        Returns:
            YOLO: An instance of the YOLO model, ready for use.

        Raises:
            FileNotFoundError: If none of the pre-configured model paths exist.
        """
        from ultralytics import YOLO

        if self.model_path is None:
            self.model_path = (
                YOLO_MODEL_EDGE_TPU_PATH
                if os.path.exists(YOLO_MODEL_EDGE_TPU_PATH)
                and is_google_coral_connected()
                else YOLO_MODEL_PATH
            )

        logger.info(f"Loading model {self.model_path}")
        try:
            self.model = YOLO(model=self.model_path, task="detect")
            logger.info(f"Model {self.model_path} loaded successfully")
        except Exception as err:
            logger.log_exception(f"Error loading model {self.model_path}", err)

        return self.model

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Called upon exiting the context (i.e. after the 'with' block).
        Ensures proper cleanup of resources tied to the YOLO model, including memory deallocation and garbage collection.

        Parameters:
            exc_type (Exception): The type of the exception raised during the execution of the 'with' block.
                                  Can be None if no exception was raised.
            exc_value (Exception): The actual exception object raised, if any.
                                  Can be None if no exception occurred.
            traceback (Traceback): The traceback object providing details on where the exception happened.
                                  Can be None if no exception occurred.
        """
        logger.info("Cleaning up model resources.")
        if exc_type is not None:
            logger.error("An exception occurred during model execution")
            logger.error(f"Exception type: {exc_type}")
            logger.error(f"Exception value: {exc_value}")

            import traceback as tb

            logger.error(f"Traceback: {''.join(tb.format_tb(traceback))}")
        del self.model
        gc.collect()
