from typing import TYPE_CHECKING, Dict, Optional

import numpy as np

if TYPE_CHECKING:
    from ultralytics.engine.results import Keypoints


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
        original_h, original_w = source.shape[:2]

        try:
            raw_results = self.hailo.run(source)
        except Exception as e:
            if verbose:
                print("Error during Hailo inference:", e)
            raise

        detections = []
        try:
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
                            "class_id": class_id,  # used later for dummy cls property
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


# from concurrent.futures import Future
# from functools import partial

# import numpy as np
# from app.core.logger import Logger

# logger = Logger(__name__)


# # These helper “container” classes mimic the ultralytics YOLO result API.
# class DetectionBox:
#     def __init__(self, xyxy, conf, cls_index, keypoints=None):
#         # xyxy must be a list or numpy array with four values
#         self.xyxy = [np.array(xyxy)]
#         self.conf = np.array([conf])  # use numpy array for consistency
#         self.cls = np.array([cls_index])
#         self.keypoints = keypoints  # optional


# class HailoResult:
#     def __init__(self, boxes, names):
#         self.boxes = boxes  # a list of DetectionBox objects
#         self.keypoints = None  # not implemented
#         self.names = names  # dictionary mapping class ids to labels


# class HailoYOLOAdapter:
#     """
#     An adapter that wraps a Hailo HEF model and provides a predict method
#     with the same interface as ultralytics YOLO.
#     """

#     def __init__(
#         self, hef_path, labels_path=None, batch_size=None, output_type="FLOAT32"
#     ):
#         from hailo_platform import HEF  # type: ignore
#         from hailo_platform import HailoSchedulingAlgorithm  # type: ignore
#         from hailo_platform import VDevice  # type: ignore

#         self.hef_path = hef_path
#         self.batch_size = batch_size
#         params = VDevice.create_params()
#         params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN

#         # Initialize the Hailo device and infer model only once.
#         self.hef = HEF(hef_path)
#         self.target = VDevice(params)
#         self.infer_model = self.target.create_infer_model(hef_path)
#         self.infer_model.set_batch_size(1 if batch_size is None else batch_size)
#         self._set_input_output(output_type)
#         self.configured_infer_model = self.infer_model.configure()

#         # (Optional) Load names/labels – if a labels file was passed
#         self.names = {}
#         if labels_path:
#             try:
#                 with open(labels_path, "r", encoding="utf-8") as f:
#                     loaded = [line.strip() for line in f if line.strip()]
#                 # Create a mapping: class id -> label
#                 self.names = {i: label for i, label in enumerate(loaded)}
#             except Exception as e:
#                 logger.error("Failed to load labels from %s: %s", labels_path, e)

#     def _set_input_output(self, output_type):
#         """
#         Set the input and output layer information for the HEF model.
#         """
#         from hailo_platform import FormatType  # type: ignore

#         input_format_type = self.hef.get_input_vstream_infos()[0].format.type
#         self.infer_model.input().set_format_type(input_format_type)
#         output_format_type = getattr(FormatType, output_type)
#         for output in self.infer_model.outputs:
#             output.set_format_type(output_format_type)
#         self.num_outputs = len(self.infer_model.outputs)

#     def _create_bindings(self):
#         """
#         Create bindings for input and output buffers.
#         """
#         output_buffers = {
#             name: np.empty(self.infer_model.output(name).shape, dtype=np.float32)
#             for name in self.infer_model.output_names
#         }
#         return self.configured_infer_model.create_bindings(
#             output_buffers=output_buffers
#         )

#     def run(self, input_data):
#         """
#         Run synchronous inference on the Hailo device.
#         Input:
#             input_data (np.ndarray): input image (for a single frame).
#         Returns:
#             Raw inference output.
#         """
#         # Hailo expects a batch dimension.
#         if input_data.ndim == 3:
#             input_data = np.expand_dims(input_data, axis=0)

#         future = Future()
#         future._has_had_error = False
#         if self.num_outputs <= 1:
#             future._intermediate_result = []
#         else:
#             future._intermediate_result = {
#                 output.name: [] for output in self.infer_model.outputs
#             }

#         # For each frame in the batch (typically a single frame)
#         for i, frame in enumerate(input_data):
#             last = i == len(input_data) - 1
#             bindings = self._create_bindings()
#             bindings.input().set_buffer(frame)
#             self.configured_infer_model.wait_for_async_ready(timeout_ms=10000)
#             self.configured_infer_model.run_async(
#                 [bindings],
#                 partial(self.callback, bindings=bindings, future=future, last=last),
#             )

#         return future.result()

#     def callback(self, completion_info, bindings, future, last):
#         if future._has_had_error:
#             return
#         elif completion_info.exception:
#             future._has_had_error = True
#             future.set_exception(completion_info.exception)
#         else:
#             if self.num_outputs <= 1:
#                 if self.batch_size is None:
#                     future._intermediate_result = bindings.output().get_buffer()
#                 else:
#                     future._intermediate_result.append(bindings.output().get_buffer())
#             else:
#                 if self.batch_size is None:
#                     for name in bindings._output_names:
#                         future._intermediate_result[name] = bindings.output(
#                             name
#                         ).get_buffer()
#                 else:
#                     for name in bindings._output_names:
#                         future._intermediate_result[name].append(
#                             bindings.output(name).get_buffer()
#                         )
#             if last:
#                 future.set_result(future._intermediate_result)

#     def predict(self, source, verbose=False, conf=0.4, task="detect", imgsz=None):
#         """
#         Mimics the YOLO.predict() interface. Expects a numpy.array (image)
#         and returns a list with one result object whose attributes (boxes, names, keypoints)
#         are arranged so that our perform_detection() function can parse it.
#         In this implementation we run inference, parse the raw Hailo output,
#         and create dummy DetectionBox objects.

#         Args:
#             source: input image (numpy array).
#             verbose: verbosity flag (passed to Hailo run, if needed).
#             conf: confidence threshold.
#             task: string task (unused, for API compatibility).
#             imgsz: image size used for scaling (optional).

#         Returns:
#             A list containing one HailoResult object.
#         """
#         # Run inference – note: your actual Hailo post-processing may differ.
#         raw_output = self.run(source)
#         # For demonstration, assume that raw_output is a list of detections per class.
#         # Each element in raw_output is assumed to be a list of detections:
#         #    detection: [y0, x0, y1, x1, score]
#         # (This is similar in spirit to the example in examples/hailo/detect.py.)
#         boxes = []
#         # Loop over classes – assume raw_output is organized by class id (0-indexed)
#         for cls_idx, detections in enumerate(raw_output):
#             for det in detections:
#                 score = float(det[4])
#                 if score < conf:
#                     continue
#                 # Rearranging detection coordinates: [y0, x0, y1, x1] -> [x0, y0, x1, y1]
#                 bbox = [det[1], det[0], det[3], det[2]]
#                 box = DetectionBox(xyxy=bbox, conf=score, cls_index=cls_idx)
#                 boxes.append(box)
#         result = HailoResult(boxes=boxes, names=self.names)
#         return [result]

#     def close(self):
#         """Clean up Hailo resources."""
#         del self.configured_infer_model
#         self.target.release()

#     def __enter__(self):
#         return self

#     def __exit__(self, exc_type, exc_value, traceback):
#         self.close()
