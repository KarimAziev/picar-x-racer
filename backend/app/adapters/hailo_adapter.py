from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from app.core.logger import Logger
from app.util.perfomance import Timer, measure_time
from app.util.video_utils import letterbox

logger = Logger(__name__)

LayerInfo = Tuple[str, Tuple[int, ...], Any]


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
        self.input_shape: Tuple[int, ...] = self.hailo.get_input_shape()
        self.names: Dict[int, str] = labels if labels is not None else {}
        self.is_pose: bool = self._detect_pose_model()
        logger.info("'%s' is_pose model='%s'", hef_path, self.is_pose)

    def _detect_pose_model(self) -> bool:
        """
        Check if this model contains keypoint predictions by examining output shapes.
        """
        info: Tuple[List[LayerInfo], List[LayerInfo]] = self.hailo.describe()
        input_layers, output_layers = info
        logger.info(
            "input_layers='%s', output_layers='%s'", input_layers, output_layers
        )
        for _, shape, _ in output_layers:
            if shape[-1] == 51:
                return True
        return False

    def predict(
        self,
        source: np.ndarray,
        verbose: Optional[bool] = False,
        conf=0.4,
        task="detect",
        imgsz: Optional[int] = None,
    ) -> List["_DummyResult"]:
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

        expected_h, expected_w = self.input_shape[:2]
        original_h, original_w = source.shape[:2]

        if (source.shape[0] != expected_h) or (source.shape[1] != expected_w):
            if verbose:
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
            with Timer("hailo.run"):
                raw_results: Any = self.hailo.run(source)
        except Exception as e:
            logger.error("Error during Hailo inference: '%s'", e)
            raise

        if self.is_pose:
            return self._pose_task(
                raw_results=raw_results, original_w=original_w, original_h=original_h
            )
        else:
            return self._detect_task(
                raw_results=raw_results,
                original_w=original_w,
                original_h=original_h,
                conf=0.4,
            )

    @measure_time
    def _pose_task(
        self, raw_results, original_w: int, original_h: int
    ) -> List["_DummyResult"]:
        from app.util.pose_util import postproc_yolov8_pose

        predictions = postproc_yolov8_pose(
            num_of_classes=1,
            raw_detections=raw_results,
            img_size=(original_w, original_h),
        )

        bboxes = predictions["bboxes"][0]  # shape: (max_detections, 4)
        scores = predictions["scores"][0]  # shape: (max_detections, 1)
        keypoints = predictions["keypoints"][0]  # shape: (max_detections, 17, 2)
        detections: List[Dict[str, Any]] = []
        num_detections = (
            int(predictions["num_detections"])
            if "num_detections" in predictions
            else bboxes.shape[0]
        )
        for i in range(num_detections):
            detection = {
                "bbox": [int(x) for x in bboxes[i].tolist()],
                "label": self.names.get(0, "0"),
                "confidence": round(float(scores[i][0]), 2),
                "keypoints": keypoints[i].tolist(),
            }
            detections.append(detection)

        dummy_result = _DummyResult(detections, names=self.names)
        dummy_result.keypoints = _DummyKeypoints(
            np.array([det["keypoints"] for det in detections])
        )
        return [dummy_result]

    @measure_time
    def _detect_task(
        self, raw_results, original_w: int, original_h: int, conf: float
    ) -> List["_DummyResult"]:
        detections = []
        for class_id, class_results in enumerate(raw_results):
            for detection in class_results:
                score = detection[4]
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
        dummy_result = _DummyResult(detections, names=self.names)
        return [dummy_result]


class _DummyResult:
    """
    A dummy result object mimicking the object returned by ultralytics YOLO.predict().
    Its “boxes” attribute is an instance of _DummyBoxes.
    """

    def __init__(self, detections: List[Dict[str, Any]], names: Dict[int, str]) -> None:
        self.boxes: _DummyBoxes = _DummyBoxes(detections, names)
        self.keypoints: Optional[_DummyKeypoints] = None


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

    def __init__(self, det: Dict[str, Any], names: Dict[int, str]) -> None:
        self._det = det
        self.names = names

    @property
    def xyxy(self) -> np.ndarray:
        """
        Return a numpy array of shape (1,4) representing bounding box coordinates.
        The expected format is [x1, y1, x2, y2].
        """
        return np.array([self._det["bbox"]])

    @property
    def conf(self) -> _Confidence:
        """Return a simple object that has an item() method."""
        return _Confidence(self._det["confidence"])

    @property
    def cls(self) -> _ClassId:
        """Return a simple object with an item() method that returns class id."""
        return _ClassId(self._det.get("class_id", 0))


class _Confidence:
    def __init__(self, value: float) -> None:
        self._value = value

    def item(self) -> float:
        return self._value


class _ClassId:
    def __init__(self, value: int) -> None:
        self._value = value

    def item(self) -> int:
        return self._value


class _DummyKeypoints:
    """
    A helper class mimicking ultralytics keypoint results. It stores
    a list of keypoints (one per detection) in the .xy attribute.
    """

    def __init__(self, keypoints: Union[List[Any], np.ndarray]) -> None:
        self.xy: Union[List[Any], np.ndarray] = keypoints

    def __len__(self) -> int:
        return len(self.xy)
