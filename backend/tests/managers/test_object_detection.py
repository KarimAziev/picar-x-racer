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


class FakeResults:
    def __init__(self, detections, segments):
        self.boxes = detections
        self.masks = FakeMasks(segments)
        self.keypoints = None


class FakeModel:
    names = {0: "person"}

    def __init__(self, results):
        self.results = results

    def predict(self, **_kwargs):
        return [self.results]


class TestObjectDetection(unittest.TestCase):
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

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bbox"], [0, 5, 100, 55])
        self.assertEqual(
            result[0].get("segments"),
            [
                [
                    {"x": 0, "y": 5},
                    {"x": 100, "y": 5},
                    {"x": 100, "y": 55},
                    {"x": 0, "y": 55},
                ]
            ],
        )


if __name__ == "__main__":
    unittest.main()
