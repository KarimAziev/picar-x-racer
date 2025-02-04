import collections
import logging
import unittest
from typing import cast
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
from app.util.video_utils import (
    calc_fps,
    encode,
    get_frame_size,
    resize_by_height_maybe,
    resize_by_width_maybe,
    resize_frame,
    resize_to_fixed_height,
)


def dummy_enhancer(frame: np.ndarray):
    """A dummy enhancer that simply adds 10 to every pixel."""
    logging.debug("dummy_enhancer frame's type=%s", type(frame))
    return frame + 10


def failing_enhancer(frame: np.ndarray):
    """A dummy enhancer that raises an exception."""
    logging.debug("failing_enhancer frame's type=%s", type(frame))
    raise ValueError("Enhancer error")


class TestVideoUtils(unittest.TestCase):

    def setUp(self):
        # a dummy a 3-channel image with uint8 type
        self.dummy_frame = np.zeros((200, 400, 3), dtype=np.uint8)

    def test_encode_without_enhancer(self):
        """Test `encode` call without passing enhancer."""
        result_bytes = encode(self.dummy_frame, format=".jpg")
        self.assertIsInstance(result_bytes, bytes)
        decoded = cv2.imdecode(np.frombuffer(result_bytes, np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape, self.dummy_frame.shape)

    def test_encode_with_valid_enhancer(self):
        """Test `encode` call with valid enhancer."""
        result_bytes = encode(
            self.dummy_frame, format=".jpg", frame_enhancer=dummy_enhancer
        )
        decoded = cv2.imdecode(np.frombuffer(result_bytes, np.uint8), cv2.IMREAD_COLOR)
        # Because the dummy enhancer adds 10, the frame should be different from self.dummy_frame.
        # We cannot compare pixel-by-pixel because JPEG encoding is lossy,
        # so we simply check that output dimensions are maintained.
        self.assertEqual(decoded.shape, self.dummy_frame.shape)

    @patch("app.util.video_utils.logger.error")
    def test_encode_with_failing_enhancer(self, mock_logger_error: MagicMock):
        """Test `encode` call with failing enhancer."""
        result_bytes = encode(
            self.dummy_frame, format=".jpg", frame_enhancer=failing_enhancer
        )
        decoded = cv2.imdecode(np.frombuffer(result_bytes, np.uint8), cv2.IMREAD_COLOR)
        mock_logger_error.assert_called_once()
        self.assertEqual(decoded.shape, self.dummy_frame.shape)

    #
    # Tests for resize_frame()
    #
    def test_resize_frame_valid(self):
        new_width = 100
        new_height = 50
        resized = resize_frame(self.dummy_frame, new_width, new_height)
        self.assertEqual(resized.shape[1], new_width)
        self.assertEqual(resized.shape[0], new_height)

    def test_resize_frame_with_none(self):
        self.assertIsNone(resize_frame(None, 100, 100))

    #
    # Tests for get_frame_size()
    #
    def test_get_frame_size_valid(self):
        width, height = get_frame_size(self.dummy_frame)
        # The dummy frame shape is (200, 400, 3) --> width=400, height=200
        self.assertEqual(width, 400)
        self.assertEqual(height, 200)

    def test_get_frame_size_none(self):
        self.assertEqual(get_frame_size(None), (None, None))

    #
    # Tests for resize_by_width_maybe()
    #
    @patch("app.util.video_utils.width_to_height")
    def test_resize_by_width_maybe_no_change(self, mocked_width_to_height):
        """
        Test `resize_by_width_maybe` call with the current width that is equal to the
        desired width, should return the original frame.
        """
        result = resize_by_width_maybe(self.dummy_frame, 400)
        self.assertTrue(np.array_equal(result, self.dummy_frame))
        mocked_width_to_height.assert_not_called()

    @patch("app.util.video_utils.width_to_height")
    def test_resize_by_width_maybe_resize(self, mocked_width_to_height: MagicMock):
        # assume that given target new width, width_to_height returns 100.
        mocked_width_to_height.return_value = 100
        result = resize_by_width_maybe(self.dummy_frame, 200)
        self.assertEqual(result.shape, (100, 200, 3))
        mocked_width_to_height.assert_called_once_with(
            200, target_width=400, target_height=200
        )

    #
    # Tests for resize_by_height_maybe()
    #
    @patch("app.util.video_utils.height_to_width")
    def test_resize_by_height_maybe_no_change(self, mocked_height_to_width: MagicMock):
        result = resize_by_height_maybe(self.dummy_frame, 200)
        self.assertTrue(np.array_equal(result, self.dummy_frame))
        mocked_height_to_width.assert_not_called()

    @patch("app.util.video_utils.height_to_width")
    def test_resize_by_height_maybe_resize(self, mocked_height_to_width: MagicMock):
        # assume that given new height, height_to_width returns 150.
        mocked_height_to_width.return_value = 150
        result = resize_by_height_maybe(self.dummy_frame, 100)
        # Check that the resulting shape is (100, 150, 3)
        self.assertEqual(result.shape, (100, 150, 3))
        mocked_height_to_width.assert_called_once_with(
            100, target_width=400, target_height=200
        )

    #
    # Tests for resize_to_fixed_height()
    #
    @patch("app.util.video_utils.height_to_width")
    def test_resize_to_fixed_height(self, mocked_height_to_width: MagicMock):
        base_size = 128
        mocked_height_to_width.return_value = 256
        resized_frame, orig_w, orig_h, new_w, new_h = resize_to_fixed_height(
            self.dummy_frame, base_size=base_size
        )
        self.assertEqual(orig_w, 400)
        self.assertEqual(orig_h, 200)
        self.assertEqual(new_h, base_size)
        self.assertEqual(new_w, 256)
        self.assertEqual(resized_frame.shape, (base_size, new_w, 3))
        mocked_height_to_width.assert_called_once_with(
            base_size,
            target_width=400,
            target_height=200,
            round_up_to_multiple=32,
        )

    def test_calc_fps_with_list(self):
        # Create timestamps for a 30 FPS sequence (approximately 0.033 sec interval)
        timestamps = [0.0, 0.033, 0.066, 0.099]

        # Without rounding, our function returns FPS as a float truncated to one decimal:
        # Expected FPS = 1/0.033 = approx 30.3, then int(30.3*10)/10 = 30.3.
        fps = calc_fps(timestamps)
        self.assertIsNotNone(fps)
        fps = cast(float, fps)
        self.assertAlmostEqual(fps, 30.3, places=1)

    def test_calc_fps_with_deque_and_round(self):
        timestamps = collections.deque([0.0, 0.040, 0.080, 0.120])
        fps = calc_fps(timestamps, round_result=True)
        self.assertEqual(fps, 25)

    def test_calc_fps_insufficient(self):
        timestamps = [1.0]
        self.assertIsNone(calc_fps(timestamps))

    def test_calc_fps_zero_delta(self):
        """Test calc_fps called with the same timestamps; time delta is 0."""

        timestamps = [1.0, 1.0, 1.0]
        self.assertIsNone(calc_fps(timestamps))


if __name__ == "__main__":
    unittest.main()
