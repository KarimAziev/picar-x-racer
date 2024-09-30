import gc
import os

from app.config.paths import YOLO_MODEL_EDGE_TPU_PATH, YOLO_MODEL_PATH
from app.util.logger import Logger

logger = Logger(__name__)


class ModelManager:
    def __enter__(self):

        from ultralytics import YOLO

        self.model = YOLO(
            (
                YOLO_MODEL_EDGE_TPU_PATH
                if os.path.exists(YOLO_MODEL_EDGE_TPU_PATH)
                else YOLO_MODEL_PATH
            ),
            task="detect",
        )
        self.model.overrides["imgsz"] = (192, 192)
        return self.model

    def __exit__(self, exc_type, exc_value, traceback):

        del self.model
        gc.collect()
