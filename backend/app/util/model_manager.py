import gc
import os

from app.config.paths import YOLO_MODEL_8_EDGE_TPU, YOLO_MODEL_8_PATH
from app.util.logger import Logger

logger = Logger(__name__)


class ModelManager:
    def __enter__(self):

        from ultralytics import YOLO

        self.model = YOLO(
            YOLO_MODEL_8_EDGE_TPU
            if os.path.exists(YOLO_MODEL_8_EDGE_TPU)
            else YOLO_MODEL_8_PATH
        )
        return self.model

    def __exit__(self, exc_type, exc_value, traceback):

        del self.model
        gc.collect()
