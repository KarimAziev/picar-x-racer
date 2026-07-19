import unittest
from typing import Any, cast

import numpy as np
from app.managers.detection.object_detection import perform_detection


class FakeScalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class FakeDetection:
    def __init__(self, bbox, confidence, class_id):
        self.xyxy = np.array([bbox], dtype=np.float32)
        self.conf = FakeScalar(confidence)
        self.cls = FakeScalar(class_id)


class FakeMasks:
    def __init__(self, segments):
        self.xy = segments


class FakeSemanticMask:
    def __init__(self, data):
        self.data = data


class FakeKeypoints:
    def __init__(self, coordinates, confidences=None):
        self.xy = np.array(coordinates, dtype=np.float32)
        self.conf = (
            np.array(confidences, dtype=np.float32) if confidences is not None else None
        )

    def __len__(self):
        return len(self.xy)


class FakeResults:
    def __init__(
        self,
        detections=None,
        segments=None,
        semantic_mask=None,
        keypoints=None,
    ):
        self.boxes = detections
        self.masks = FakeMasks(segments or [])
        self.keypoints = keypoints
        self.semantic_mask = (
            FakeSemanticMask(semantic_mask) if semantic_mask is not None else None
        )
        self.names = {0: "road", 1: "person", 2: "car"}


class FakeModel:
    names = {0: "person"}

    def __init__(self, results):
        self.results = results

    def predict(self, **_kwargs):
        return [self.results]


class TestObjectDetection(unittest.TestCase):
    def test_perform_detection_preserves_pose_keypoint_confidence(self):
        detection = FakeDetection(
            bbox=[10, 10, 90, 90],
            confidence=0.9,
            class_id=0,
        )
        keypoints = FakeKeypoints(
            coordinates=[[[20, 30], [40, 50]]],
            confidences=[[0.95, 0.12345]],
        )
        model = FakeModel(FakeResults([detection], keypoints=keypoints))

        result = perform_detection(
            frame=np.zeros((100, 100, 3), dtype=np.uint8),
            yolo_model=cast(Any, model),
            resized_height=100,
            resized_width=100,
            original_width=100,
            original_height=100,
            pad_top=0,
            pad_left=0,
            confidence_threshold=0.4,
        )

        self.assertEqual(
            result["detection_result"][0].get("keypoints"),
            [
                {"x": 20, "y": 30, "confidence": 0.95},
                {"x": 40, "y": 50, "confidence": 0.1235},
            ],
        )

    def test_perform_detection_maps_segmentation_polygon_to_original_frame(self):
        detection = FakeDetection(
            bbox=[10, 5, 60, 55],
            confidence=0.9,
            class_id=0,
        )
        segment = np.array(
            [
                [10, 5],
                [60, 5],
                [60, 55],
                [10, 55],
            ],
            dtype=np.float32,
        )
        model = FakeModel(FakeResults([detection], [segment]))

        result = perform_detection(
            frame=np.zeros((100, 100, 3), dtype=np.uint8),
            yolo_model=cast(Any, model),
            resized_height=100,
            resized_width=100,
            original_width=200,
            original_height=100,
            pad_top=0,
            pad_left=10,
            confidence_threshold=0.4,
        )

        detections = result["detection_result"]
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0]["bbox"], [0, 5, 100, 55])
        self.assertEqual(
            detections[0].get("segments"),
            [
                [
                    {"x": 0, "y": 5},
                    {"x": 100, "y": 5},
                    {"x": 100, "y": 55},
                    {"x": 0, "y": 55},
                ]
            ],
        )

    def test_perform_detection_simplifies_dense_segmentation_polygon(self):
        detection = FakeDetection(
            bbox=[0, 0, 100, 100],
            confidence=0.9,
            class_id=0,
        )
        top = [[x, 0] for x in np.linspace(0, 100, 125)]
        right = [[100, y] for y in np.linspace(0, 100, 125)]
        bottom = [[x, 100] for x in np.linspace(100, 0, 125)]
        left = [[0, y] for y in np.linspace(100, 0, 125)]
        segment = np.array(top + right + bottom + left, dtype=np.float32)
        model = FakeModel(FakeResults([detection], [segment]))

        result = perform_detection(
            frame=np.zeros((100, 100, 3), dtype=np.uint8),
            yolo_model=cast(Any, model),
            resized_height=100,
            resized_width=100,
            original_width=100,
            original_height=100,
            pad_top=0,
            pad_left=0,
            confidence_threshold=0.4,
        )

        segments = result["detection_result"][0].get("segments")
        self.assertIsNotNone(segments)
        if segments is None:
            self.fail("Expected segmentation points")
        self.assertLessEqual(len(segments[0]), 8)

    def test_perform_detection_encodes_semantic_mask(self):
        semantic_mask = np.array(
            [
                [0, 0, 1, 1],
                [0, 2, 2, 1],
            ],
            dtype=np.uint8,
        )
        model = FakeModel(FakeResults(semantic_mask=semantic_mask))

        result = perform_detection(
            frame=np.zeros((2, 4, 3), dtype=np.uint8),
            yolo_model=cast(Any, model),
            resized_height=2,
            resized_width=4,
            original_width=4,
            original_height=2,
            pad_top=0,
            pad_left=0,
            confidence_threshold=0.4,
        )

        self.assertEqual(result["detection_result"], [])
        self.assertEqual(
            result.get("semantic_mask"),
            {
                "width": 4,
                "height": 2,
                "counts": [[0, 2], [1, 2], [0, 1], [2, 2], [1, 1]],
                "classes": {0: "road", 1: "person", 2: "car"},
            },
        )

    def test_perform_detection_filters_semantic_mask_classes(self):
        semantic_mask = np.array([[0, 1, 2]], dtype=np.uint8)
        model = FakeModel(FakeResults(semantic_mask=semantic_mask))

        result = perform_detection(
            frame=np.zeros((1, 3, 3), dtype=np.uint8),
            yolo_model=cast(Any, model),
            resized_height=1,
            resized_width=3,
            original_width=3,
            original_height=1,
            pad_top=0,
            pad_left=0,
            labels_to_detect=["car"],
            confidence_threshold=0.4,
        )

        semantic_result = result.get("semantic_mask")
        self.assertIsNotNone(semantic_result)
        if semantic_result is None:
            self.fail("Expected semantic mask")
        self.assertEqual(semantic_result["counts"], [[0, 1], [1, 1], [2, 1]])
        self.assertEqual(semantic_result["classes"], {2: "car"})


if __name__ == "__main__":
    unittest.main()
