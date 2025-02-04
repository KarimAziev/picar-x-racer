import os
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Tuple, Type

from app.config.config import settings
from app.core.logger import Logger
from app.util.file_util import resolve_absolute_path
from app.util.google_coral import is_google_coral_connected

logger = Logger(__name__)

if TYPE_CHECKING:
    from ultralytics import YOLO


class ModelManager:
    """
    ModelManager class is a context manager used for loading and managing the lifecycle of a YOLO object detection model.

    This class ensures that the model is loaded when entering the context and properly cleaned up upon exiting the context.
    The model loading path is selected dynamically based on available files.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        """
        Initializes the ModelManager with an optional model path.

        Parameters:
            model_path (str): An optional custom path to use for loading the model.
        """
        self.model: Optional["YOLO"] = None
        self.error_msg = None
        self.model_path = (
            resolve_absolute_path(model_path, settings.DATA_DIR)
            if model_path is not None
            else model_path
        )

    def __enter__(self) -> Tuple[Optional["YOLO"], Optional[str]]:
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
        try:
            from ultralytics import YOLO

            if self.model_path is None:
                self.model_path = (
                    settings.YOLO_MODEL_EDGE_TPU_PATH
                    if os.path.exists(settings.YOLO_MODEL_EDGE_TPU_PATH)
                    and is_google_coral_connected()
                    else settings.YOLO_MODEL_PATH
                )

            logger.info(f"Loading model {self.model_path}")
            try:
                self.model = YOLO(model=self.model_path, task="detect")
                logger.info(f"Model {self.model_path} loaded successfully")
            except FileNotFoundError:
                msg = f"Model's file {self.model_path} is not found"
                logger.error(msg)
                self.error_msg = msg
            except Exception:
                msg = f"Unexpected error while loading {self.model_path}"
                logger.error(msg, exc_info=True)
                self.error_msg = msg

            return self.model, self.error_msg
        except KeyboardInterrupt:
            logger.warning("Detection model context received KeyboardInterrupt.")
            return self.model, "Detection model context received KeyboardInterrupt."

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
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
            logger.error(f"Exception type: {exc_type.__name__}")
            if exc_value:
                logger.error(f"Exception value: {exc_value}")

            import traceback as tb

            if traceback:
                logger.error(f"Traceback: {''.join(tb.format_tb(traceback))}")
        del self.model
