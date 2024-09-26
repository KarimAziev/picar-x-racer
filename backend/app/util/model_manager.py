import gc

from app.config.paths import YOLO_MODEL_8_PATH
from app.util.logger import Logger

logger = Logger(__name__)


class ModelManager:
    def __enter__(self):

        from ultralytics import YOLO

        self.model = YOLO(YOLO_MODEL_8_PATH)
        return self.model

    def __exit__(self, exc_type, exc_value, traceback):

        del self.model
        gc.collect()
