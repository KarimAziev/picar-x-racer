from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from app.core.logger import Logger
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
    ) -> None:
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
            from picamera2.devices.hailo.hailo import Hailo  # type: ignore
        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Hailo module could not be imported: %s", str(e))
            raise

        self.hailo = Hailo(hef_path, batch_size=batch_size, output_type=output_type)
        self._closed = False
        try:
            self.input_shape: Tuple[int, ...] = self.hailo.get_input_shape()
            self.names: Dict[int, str] = labels if labels is not None else {}
            self.is_pose: bool = self._detect_pose_model()
        except Exception:
            self.close()
            raise
        logger.info("'%s' is pose model='%s'", hef_path, self.is_pose)

    def close(self) -> None:
        """Release the configured model and its reference to the Hailo device."""
        if not self._closed:
            self._closed = True
            self.hailo.close()

    def _detect_pose_model(self) -> bool:
        """
        Check if this model contains keypoint predictions by examining output shapes.
        """
        info: Tuple[List[LayerInfo], List[LayerInfo]] = self.hailo.describe()
        input_layers, output_layers = info
        self.is_segmentation = any(
            shape == (self.input_shape[0] // 4, self.input_shape[1] // 4, 32)
            for _, shape, _ in output_layers
        )
        self.is_depth = len(output_layers) == 1 and output_layers[0][0].startswith(
            "scdepthv3/"
        )
        if self.is_depth:
            self.names = {}
        logger.debug(
            "Input layers='%s', output layers='%s'", input_layers, output_layers
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
        iou: Optional[float] = None,
        max_det: Optional[int] = None,
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
            iou: Host NMS threshold for pose and instance segmentation.
            max_det: Host NMS result limit for pose and instance segmentation.
            task: Task string (ignored, kept for interface compatibility).
            imgsz: The image size used for inference.

        Returns:
            list: A list containing one dummy result object.
        """

        expected_h, expected_w = self.input_shape[:2]
        original_h, original_w = source.shape[:2]
        resized_w, resized_h = original_w, original_h
        pad_left = pad_top = 0

        if (source.shape[0] != expected_h) or (source.shape[1] != expected_w):
            logger.debug(
                f"Letterboxing input from {source.shape[:2]} to {(expected_h, expected_w)}"
            )

            (
                source,
                _,
                _,
                resized_w,
                resized_h,
                pad_left,
                pad_top,
            ) = letterbox(source, expected_w, expected_h)

        try:
            raw_results: Any = self.hailo.run(source)

        except Exception as e:
            logger.error("Error during Hailo inference: '%s'", e)
            raise

        if self.is_pose:
            results = self._pose_task(
                raw_results=raw_results,
                original_w=expected_w,
                original_h=expected_h,
                conf=conf,
                iou=iou if iou is not None else 0.7,
                max_det=max_det if max_det is not None else 300,
            )
        elif self.is_segmentation:
            results = self._segmentation_task(
                raw_results,
                conf,
                iou if iou is not None else 0.7,
                max_det if max_det is not None else 300,
            )
        elif self.is_depth:
            result = _DummyResult([], self.names)
            logits = np.asarray(raw_results).squeeze()
            depth = 1.0 / (10.0 / (1.0 + np.exp(-np.clip(logits, -80, 80))) + 0.009)
            depth = cv2.resize(
                depth, (expected_w, expected_h), interpolation=cv2.INTER_LINEAR
            )
            result.depth = cv2.resize(
                depth[pad_top : pad_top + resized_h, pad_left : pad_left + resized_w],
                (original_w, original_h),
                interpolation=cv2.INTER_LINEAR,
            )
            return [result]
        else:
            return self._detect_task(
                raw_results=raw_results,
                original_w=original_w,
                original_h=original_h,
                conf=conf,
                resized_w=resized_w,
                resized_h=resized_h,
                pad_left=pad_left,
                pad_top=pad_top,
            )

        def restore(points: np.ndarray) -> np.ndarray:
            adjusted = np.asarray(points, dtype=np.float32).copy()
            adjusted[..., 0] = np.clip(
                (adjusted[..., 0] - pad_left) * original_w / resized_w, 0, original_w
            )
            adjusted[..., 1] = np.clip(
                (adjusted[..., 1] - pad_top) * original_h / resized_h, 0, original_h
            )
            return adjusted

        for result in results:
            for detection in result.boxes._detections:
                detection["bbox"] = (
                    restore(np.asarray(detection["bbox"]).reshape(2, 2))
                    .reshape(4)
                    .tolist()
                )
            if result.keypoints is not None:
                result.keypoints.xy = restore(np.asarray(result.keypoints.xy))
            if result.masks is not None:
                result.masks.xy = [restore(polygon) for polygon in result.masks.xy]
        return results

    def _pose_task(
        self,
        raw_results,
        original_w: int,
        original_h: int,
        conf: float,
        iou: float,
        max_det: int,
    ) -> List["_DummyResult"]:
        from app.util.pose_util import postproc_yolov8_pose

        predictions = postproc_yolov8_pose(
            num_of_classes=1,
            raw_detections=raw_results,
            img_size=(original_w, original_h),
            confidence=conf,
            iou=iou,
            max_detections=max_det,
        )

        bboxes = predictions["bboxes"][0]  # shape: (max_detections, 4)
        scores = predictions["scores"][0]  # shape: (max_detections, 1)
        keypoints = predictions["keypoints"][0]  # shape: (max_detections, 17, 2)
        detections: List[Dict[str, Any]] = []
        num_detections = bboxes.shape[0]
        for i in range(num_detections):
            if scores[i][0] <= 0 or scores[i][0] < conf:
                continue
            detection = {
                "bbox": [int(x) for x in bboxes[i].tolist()],
                "label": self.names.get(0, "0"),
                "confidence": round(float(scores[i][0]), 2),
                "keypoints": keypoints[i].tolist(),
            }
            detections.append(detection)

        dummy_result = _DummyResult(detections, names=self.names)
        dummy_result.keypoints = _DummyKeypoints(
            np.array([det["keypoints"] for det in detections]).reshape(
                -1, keypoints.shape[1], 2
            ),
            predictions["joint_scores"][
                0, (scores[:, 0] > 0) & (scores[:, 0] >= conf), :, 0
            ],
        )
        return [dummy_result]

    def _segmentation_task(
        self, raw_results, conf: float, iou: float, max_det: int
    ) -> List["_DummyResult"]:
        from app.util.hailo_segmentation import decode_yolov8_segmentation

        boxes, scores, classes, polygons = decode_yolov8_segmentation(
            raw_results, self.input_shape, conf, iou, max_det
        )
        detections = [
            {
                "bbox": box.tolist(),
                "confidence": float(score),
                "class_id": int(class_id),
            }
            for box, score, class_id in zip(boxes, scores, classes)
        ]
        result = _DummyResult(detections, self.names)
        result.masks = _DummyMasks(polygons)
        return [result]

    def _detect_task(
        self,
        raw_results,
        original_w: int,
        original_h: int,
        conf: float,
        resized_w: int,
        resized_h: int,
        pad_left: int,
        pad_top: int,
    ) -> List["_DummyResult"]:
        detections: List[Dict[str, Any]] = []
        input_h, input_w = self.input_shape[:2]
        scale_x, scale_y = original_w / resized_w, original_h / resized_h
        for class_id, class_results in enumerate(raw_results):
            for detection in class_results:
                score = detection[4]
                if score < conf:
                    continue
                y0, x0, y1, x1 = detection[:4]
                bbox = [
                    int(np.clip((x0 * input_w - pad_left) * scale_x, 0, original_w)),
                    int(np.clip((y0 * input_h - pad_top) * scale_y, 0, original_h)),
                    int(np.clip((x1 * input_w - pad_left) * scale_x, 0, original_w)),
                    int(np.clip((y1 * input_h - pad_top) * scale_y, 0, original_h)),
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
        self.masks: Optional[_DummyMasks] = None
        self.depth: Optional[np.ndarray] = None


class _DummyMasks:
    """Instance polygons in source-frame pixel coordinates."""

    def __init__(self, polygons: List[np.ndarray]) -> None:
        self.xy = polygons


class _DummyBoxes:
    """
    A dummy boxes container that can be iterated over.
    Each iteration returns a _DummyDetection.
    """

    def __init__(self, detections, names: Dict) -> None:
        self._detections = detections
        self.names = names

    def __iter__(self) -> Iterator[_DummyDetection]:
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

    def __init__(
        self,
        keypoints: Union[List[Any], np.ndarray],
        confidence: Optional[np.ndarray] = None,
    ) -> None:
        self.xy: Union[List[Any], np.ndarray] = keypoints
        self.conf = confidence

    def __len__(self) -> int:
        return len(self.xy)
