import unittest

import numpy as np

from app.util.hailo_segmentation import decode_yolov8_segmentation


class TestHailoSegmentation(unittest.TestCase):
    def outputs(self):
        outputs = {"proto": np.ones((8, 8, 32), dtype=np.float32)}
        for stride in (8, 16, 32):
            side = 32 // stride
            boxes = np.full((side, side, 4, 16), -100, dtype=np.float32)
            boxes[..., 1] = 100
            outputs[f"box{stride}"] = boxes.reshape(side, side, 64)
            outputs[f"score{stride}"] = np.zeros((side, side, 80), dtype=np.float32)
            outputs[f"mask{stride}"] = np.ones((side, side, 32), dtype=np.float32)
        return outputs

    def test_decodes_boxes_and_crops_mask_to_instance(self):
        outputs = self.outputs()
        outputs["score8"][1, 1, 3] = 0.9
        boxes, scores, classes, polygons = decode_yolov8_segmentation(
            outputs, (32, 32, 3), 0.4, 0.7, 10
        )
        np.testing.assert_allclose(boxes, [[4, 4, 20, 20]])
        np.testing.assert_allclose(scores, [0.9])
        self.assertEqual(classes.tolist(), [3])
        self.assertEqual(len(polygons), 1)
        self.assertTrue(np.all(polygons[0] >= 4))
        self.assertTrue(np.all(polygons[0] <= 20))

    def test_empty_frame_and_threshold(self):
        outputs = self.outputs()
        outputs["score8"][1, 1, 0] = 0.3
        boxes, _, _, polygons = decode_yolov8_segmentation(
            outputs, (32, 32, 3), 0.4, 0.7, 10
        )
        self.assertEqual(boxes.shape, (0, 4))
        self.assertEqual(polygons, [])
