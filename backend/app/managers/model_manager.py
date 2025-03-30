from __future__ import annotations

import os
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Tuple, Type, Union

from app.config.config import settings
from app.core.logger import Logger
from app.util.file_util import resolve_absolute_path
from app.util.google_coral import is_google_coral_connected

logger = Logger(__name__)


if TYPE_CHECKING:
    from app.adapters.hailo_adapter import YOLOHailoAdapter
    from ultralytics import YOLO


class ModelManager:
    """
    ModelManager is a context manager for loading and managing a YOLO detection model.
    It supports both standard ultralytics YOLO and Hailo HEF models via an adapter.
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model = None
        self.error_msg = None
        self.model_path = (
            resolve_absolute_path(model_path, settings.DATA_DIR)
            if model_path is not None
            else model_path
        )

    def __enter__(
        self,
    ) -> Tuple[Union["YOLO", "YOLOHailoAdapter", None], Optional[str]]:
        try:
            if self.model_path and self.model_path.endswith(".hef"):
                logger.info(f"Loading Hailo model {self.model_path}")
                try:
                    from app.adapters.hailo_adapter import YOLOHailoAdapter
                except ImportError as e:
                    msg = f"Failed to import Hailo adapter: {e}"
                    logger.error(msg)
                    self.error_msg = msg
                    return None, self.error_msg

                labels = {}

                if (
                    hasattr(settings, "HAILO_LABELS")
                    and settings.HAILO_LABELS is not None
                    and os.path.exists(
                        resolve_absolute_path(settings.HAILO_LABELS, settings.DATA_DIR)
                    )
                ):
                    with open(settings.HAILO_LABELS, "r", encoding="utf-8") as f:
                        lines = f.read().splitlines()
                        for idx, name in enumerate(lines):
                            labels[idx] = name
                self.model = YOLOHailoAdapter(self.model_path, labels=labels)
                logger.info("Hailo model loaded successfully")
            else:
                from ultralytics import YOLO

                if YOLO is None:
                    msg = "ultralytics YOLO not available."
                    logger.error(msg)
                    self.error_msg = msg
                else:
                    if self.model_path is None:
                        if (
                            os.path.exists(settings.YOLO_MODEL_EDGE_TPU_PATH)
                            and is_google_coral_connected()
                        ):
                            self.model_path = settings.YOLO_MODEL_EDGE_TPU_PATH
                        else:
                            self.model_path = settings.YOLO_MODEL_PATH
                    logger.info(f"Loading YOLO model {self.model_path}")
                    try:
                        self.model = YOLO(model=self.model_path, task="detect")
                        logger.info("YOLO model loaded successfully")
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
