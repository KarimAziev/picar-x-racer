from typing import TYPE_CHECKING, Dict, Optional

import numpy as np
from app.core.logger import Logger
from app.util.video_utils import letterbox

if TYPE_CHECKING:
    from ultralytics.engine.results import Keypoints

logger = Logger(__name__)


class YOLOHailoAdapter:
    def __init__(
        self,
        hef_path: str,
        batch_size: Optional[int] = None,
        output_type: str = "FLOAT32",
        labels: Optional[Dict] = None,
    ):
        """
        Initialize the Hailo adapter.

        Args:
            hef_path: Path to the HEF model file.
            batch_size: Batch size for inference.
            output_type: Desired output type (passed to Hailo API).
            labels: Optional mapping from class indices to names.
                           If not provided, indices will be converted to strings.
        """
        try:
            from picamera2.devices.hailo.hailo import Hailo
        except ImportError as e:
            raise ImportError(
                "Hailo module could not be imported. Ensure hailo dependencies are installed."
            ) from e

        self.hailo = Hailo(hef_path, batch_size=batch_size, output_type=output_type)
        self.input_shape = self.hailo.get_input_shape()
        self.names = labels if labels is not None else {}

    def predict(
        self,
        source,
        verbose: Optional[bool] = False,
        conf=0.4,
        task="detect",
        imgsz: Optional[int] = None,
    ):
        """
        Mimics the ultralytics YOLO predict() method.
        It:
          – Runs inference on the source image using the Hailo API.
          – Performs post-processing that scales the Hailo outputs into the original image space.
          – Returns a list with a dummy “result” that has a “boxes” attribute
            that can be iterated to yield detection entries.

        Args:
            source: Input image (frame).
            verbose: Controls verbosity.
            conf: Confidence threshold.
            task: Task string (ignored, kept for interface compatibility).
            imgsz: The image size used for inference.

        Returns:
            list: A list containing one dummy result object.
        """
        expected_shape = self.input_shape
        expected_h, expected_w = expected_shape[:2]
        original_h, original_w = source.shape[:2]

        if (source.shape[0] != expected_h) or (source.shape[1] != expected_w):
            logger.info(
                f"Letterboxing input from {source.shape[:2]} to {(expected_h, expected_w)}"
            )

            (
                source,
                _,
                _,
                _,
                _,
                _,
                _,
            ) = letterbox(source, expected_w, expected_h)

        try:
            raw_results = self.hailo.run(source)
        except Exception as e:
            logger.error("Error during Hailo inference: %s", e)
            raise

        detections = []
        try:
            for class_id, class_results in enumerate(raw_results):
                for detection in class_results:
                    logger.info("class id='%s', detection='%s'", class_id, detection)
                    score = detection[4] if len(detection) >= 4 else conf
                    if score < conf:
                        continue
                    y0, x0, y1, x1 = detection[:4]
                    bbox = [
                        int(x0 * original_w),
                        int(y0 * original_h),
                        int(x1 * original_w),
                        int(y1 * original_h),
                    ]
                    label = self.names.get(class_id, str(class_id))
                    detections.append(
                        {
                            "bbox": bbox,
                            "label": label,
                            "confidence": round(float(score), 2),
                            "class_id": class_id,
                        }
                    )
        except Exception as e:
            if verbose:
                print("Error processing Hailo output:", e)
            raise

        dummy_result = _DummyResult(detections, names=self.names)
        return [dummy_result]


class _DummyResult:
    """
    A dummy result object mimicking the object returned by ultralytics YOLO.predict().
    Its “boxes” attribute is an instance of _DummyBoxes.
    """

    def __init__(self, detections, names: Dict):
        self.boxes = _DummyBoxes(detections, names)
        self.keypoints: Optional["Keypoints"] = None


class _DummyBoxes:
    """
    A dummy boxes container that can be iterated over.
    Each iteration returns a _DummyDetection.
    """

    def __init__(self, detections, names: Dict):
        self._detections = detections
        self.names = names

    def __iter__(self):
        for det in self._detections:
            yield _DummyDetection(det, self.names)


class _DummyDetection:
    """
    A dummy detection object that mimics one detection from ultralytics (with properties: xyxy, conf, cls).
    """

    def __init__(self, det: Dict, names: Dict):
        self._det = det
        self.names = names

    @property
    def xyxy(self):
        """
        Return a numpy array of shape (1,4) representing bounding box coordinates.

        The expected format is [x1, y1, x2, y2]"""

        return np.array([self._det["bbox"]])

    @property
    def conf(self):
        """Return a simple object that has an item() method."""

        class Conf:
            def __init__(self, value):
                self._value = value

            def item(self):
                return self._value

        return Conf(self._det["confidence"])

    @property
    def cls(self):
        """Return a simple object with an item() method that returns class id."""

        class Cls:
            def __init__(self, value):
                self._value = value

            def item(self):
                return self._value

        return Cls(self._det.get("class_id", 0))
