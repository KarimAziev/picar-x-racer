import unittest

import numpy as np
from app.schemas.detection import DetectionSettings, OverlayStyle
from app.schemas.stream import ImageRotation
from app.types.detection import DetectionQueueData
from app.util.photo import prepare_photo_frame, should_render_detection_overlay


class TestPhotoUtils(unittest.TestCase):
    def test_should_render_detection_overlay_when_recent(self):
        self.assertTrue(should_render_detection_overlay(10.5, 10.0, 1.0))

    def test_should_not_render_detection_overlay_when_stale(self):
        self.assertFalse(should_render_detection_overlay(12.0, 10.0, 1.0))

    def test_prepare_photo_frame_renders_detection_overlay(self):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        detection_settings = DetectionSettings(
            model="yolo11n.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=1.0,
            overlay_style=OverlayStyle.BOX,
        )
        detection_state: DetectionQueueData = {
            "detection_result": [
                {
                    "bbox": [10, 10, 40, 40],
                    "label": "person",
                    "confidence": 0.95,
                }
            ],
            "timestamp": 10.0,
        }

        result = prepare_photo_frame(
            frame=frame,
            rotation=ImageRotation.rotate_0,
            detection_settings=detection_settings,
            detection_state=detection_state,
            frame_timestamp=10.2,
        )

        self.assertEqual(tuple(result[10, 10]), (191, 255, 0))
        self.assertTrue(np.array_equal(frame, np.zeros((80, 80, 3), dtype=np.uint8)))

    def test_prepare_photo_frame_skips_stale_detection_overlay(self):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        detection_settings = DetectionSettings(
            model="yolo11n.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=0.5,
            overlay_style=OverlayStyle.BOX,
        )
        detection_state: DetectionQueueData = {
            "detection_result": [
                {
                    "bbox": [10, 10, 40, 40],
                    "label": "person",
                    "confidence": 0.95,
                }
            ],
            "timestamp": 10.0,
        }

        result = prepare_photo_frame(
            frame=frame,
            rotation=ImageRotation.rotate_0,
            detection_settings=detection_settings,
            detection_state=detection_state,
            frame_timestamp=11.0,
        )

        self.assertTrue(np.array_equal(result, frame))

    def test_prepare_photo_frame_skips_detection_overlay_when_disabled(self):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        detection_settings = DetectionSettings(
            model="yolo11n.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=1.0,
            overlay_style=OverlayStyle.BOX,
        )
        detection_state: DetectionQueueData = {
            "detection_result": [
                {
                    "bbox": [10, 10, 40, 40],
                    "label": "person",
                    "confidence": 0.95,
                }
            ],
            "timestamp": 10.0,
        }

        result = prepare_photo_frame(
            frame=frame,
            rotation=ImageRotation.rotate_0,
            detection_settings=detection_settings,
            detection_state=detection_state,
            frame_timestamp=10.2,
            render_detection_overlay=False,
        )

        self.assertTrue(np.array_equal(result, frame))

    def test_prepare_photo_frame_rotates_after_overlay(self):
        frame = np.zeros((40, 80, 3), dtype=np.uint8)
        detection_settings = DetectionSettings(
            model="yolo11n.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=1.0,
            overlay_style=OverlayStyle.BOX,
        )
        detection_state: DetectionQueueData = {
            "detection_result": [
                {
                    "bbox": [5, 5, 25, 20],
                    "label": "person",
                    "confidence": 0.95,
                }
            ],
            "timestamp": 10.0,
        }

        result = prepare_photo_frame(
            frame=frame,
            rotation=ImageRotation.rotate_90,
            detection_settings=detection_settings,
            detection_state=detection_state,
            frame_timestamp=10.1,
        )

        self.assertEqual(result.shape, (80, 40, 3))
        self.assertTrue(np.any(result[:, :, 1] == 255))

    def test_prepare_photo_frame_renders_segment_without_bbox(self):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        detection_settings = DetectionSettings(
            model="yolo11n-seg.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=1.0,
            overlay_style=OverlayStyle.NO_BBOX_SEGMENT,
        )
        detection_state: DetectionQueueData = {
            "detection_result": [
                {
                    "bbox": [10, 10, 50, 50],
                    "label": "person",
                    "confidence": 0.95,
                    "segments": [
                        [
                            {"x": 20, "y": 20},
                            {"x": 40, "y": 20},
                            {"x": 40, "y": 40},
                            {"x": 20, "y": 40},
                        ]
                    ],
                }
            ],
            "timestamp": 10.0,
        }

        result = prepare_photo_frame(
            frame=frame,
            rotation=ImageRotation.rotate_0,
            detection_settings=detection_settings,
            detection_state=detection_state,
            frame_timestamp=10.2,
        )

        self.assertTrue(np.any(result[20:41, 20:41, 1] > 0))
        self.assertTrue(np.array_equal(result[10, 10], np.zeros(3, dtype=np.uint8)))

    def test_prepare_photo_frame_renders_semantic_mask(self):
        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        detection_settings = DetectionSettings(
            model="yolo26n-sem.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=1.0,
            overlay_style=OverlayStyle.SEMANTIC,
        )
        detection_state: DetectionQueueData = {
            "detection_result": [],
            "semantic_mask": {
                "width": 2,
                "height": 2,
                "counts": [[0, 1], [1, 3]],
                "classes": {0: "background", 1: "road"},
            },
            "timestamp": 10.0,
        }

        result = prepare_photo_frame(
            frame=frame,
            rotation=ImageRotation.rotate_0,
            detection_settings=detection_settings,
            detection_state=detection_state,
            frame_timestamp=10.2,
        )

        self.assertTrue(np.array_equal(result[0, 0], frame[0, 0]))
        self.assertFalse(np.array_equal(result[79, 79], frame[79, 79]))


if __name__ == "__main__":
    unittest.main()
