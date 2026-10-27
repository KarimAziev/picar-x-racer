import base64
import unittest

import numpy as np

from app.util.depth import encode_depth_map, draw_depth_map


class TestDepthMap(unittest.TestCase):
    def test_encoding_preserves_direction_and_limits_resolution(self):
        depth = np.tile(np.linspace(1, 10, 640), (480, 1))
        data = encode_depth_map(depth, max_side=160)
        self.assertEqual((data["width"], data["height"]), (160, 120))
        self.assertEqual(data["units"], "relative")
        values = np.frombuffer(base64.b64decode(data["data"]), dtype=np.uint8).reshape(
            120, 160
        )
        self.assertEqual(values[0, 0], 0)
        self.assertEqual(values[0, -1], 255)
        frame = draw_depth_map(np.zeros((240, 320, 3), dtype=np.uint8), data)
        self.assertEqual(frame.shape, (240, 320, 3))
        self.assertGreater(frame[0, 0, 2], frame[0, 0, 0])
        self.assertGreater(frame[0, -1, 0], frame[0, -1, 2])

    def test_constant_and_nonfinite_output(self):
        data = encode_depth_map(np.full((8, 8), np.nan))
        self.assertEqual(set(base64.b64decode(data["data"])), {0})
        self.assertEqual(data["near"], 0)
        self.assertEqual(data["far"], 0)
