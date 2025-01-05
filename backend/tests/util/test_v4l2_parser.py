import subprocess
import unittest
from unittest.mock import Mock, patch

from app.util.v4l2_parser import V4L2FormatParser


class TestV4L2FormatParser(unittest.TestCase):

    def setUp(self):
        self.device = "/dev/video2"
        self.parser = V4L2FormatParser(self.device)
        V4L2FormatParser.get_fps_intervals.cache_clear()

    def test_parse_discrete_resolution(self):
        """
        Test parsing of `v4l2-ctl --list-formats-ext` output with discrete resolutions.
        """
        v4l2_output = (
            "ioctl: VIDIOC_ENUM_FMT\n"
            "    Type: Video Capture\n\n"
            "    [0]: 'GREY' (8-bit Greyscale)\n"
            "        Size: Discrete 640x360\n"
            "            Interval: Discrete 0.067s (15.000 fps)\n"
            "            Interval: Discrete 0.033s (30.000 fps)\n"
        )

        expected_result = [
            {
                'key': '/dev/video2:GREY:640x360',
                'label': 'GREY, 640x360',
                'children': [
                    {
                        'device': '/dev/video2',
                        'width': 640,
                        'height': 360,
                        'pixel_format': 'GREY',
                        'key': '/dev/video2:GREY:640x360:15',
                        'label': 'GREY, 640x360, 15 fps',
                        'fps': 15,
                    },
                    {
                        'device': '/dev/video2',
                        'width': 640,
                        'height': 360,
                        'pixel_format': 'GREY',
                        'key': '/dev/video2:GREY:640x360:30',
                        'label': 'GREY, 640x360, 30 fps',
                        'fps': 30,
                    },
                ],
            }
        ]

        result = self.parser.parse(v4l2_output)
        self.assertEqual(result, expected_result)

    @patch("app.util.v4l2_parser.V4L2FormatParser.get_fps_intervals")
    def test_parse_stepwise_resolution(self, mock_get_fps_intervals: Mock):
        """
        Test parsing of `v4l2-ctl --list-formats-ext` output with stepwise resolutions.
        """
        v4l2_output = (
            "    [1]: 'MJPG' (Motion-JPEG)\n"
            "        Size: Stepwise 320x240 - 1280x720 with step 16/16\n"
        )

        mock_get_fps_intervals.return_value = (1, 90)

        expected_result = [
            {
                'key': '/dev/video2:MJPG:320x240 - 1280x720',
                'label': 'MJPG 320x240 - 1280x720',
                'device': '/dev/video2',
                'pixel_format': 'MJPG',
                'min_width': 320,
                'max_width': 1280,
                'min_height': 240,
                'max_height': 720,
                'height_step': 16,
                'width_step': 16,
                'min_fps': 1,
                'max_fps': 90,
            }
        ]

        result = self.parser.parse(v4l2_output)
        self.assertEqual(result, expected_result)
        mock_get_fps_intervals.assert_called_once_with(
            self.device, width=320, height=240, pixel_format="MJPG"
        )

    def test_parse_empty_output(self):
        """
        Test that an empty output results in an empty list of formats.
        """
        v4l2_output = ""
        result = self.parser.parse(v4l2_output)
        self.assertEqual(result, [])

    def test_parse_invalid_output(self):
        """
        Test that invalid or unexpected output does not raise an exception but results in an empty list.
        """
        v4l2_output = "Invalid Output"
        result = self.parser.parse(v4l2_output)
        self.assertEqual(result, [])

    def test_parse_frameinterval_continuous(self):
        """
        Test parsing of `ioctl: VIDIOC_ENUM_FRAMEINTERVALS` output for continuous intervals.
        """
        frameinterval_output = (
            "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\n"
            "        Interval: Continuous 0.011s - 1.000s (1.000-90.000 fps)"
        )
        expected_result = (1, 90)
        result = V4L2FormatParser.parse_frameinterval(frameinterval_output)
        self.assertEqual(result, expected_result)

    def test_parse_frameinterval_discrete(self):
        """
        Test parsing of `ioctl: VIDIOC_ENUM_FRAMEINTERVALS` output for discrete intervals.
        """
        frameinterval_output = (
            "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\n"
            "        Interval: Discrete 0.033s (30.000 fps)"
        )
        expected_result = (30, 30)
        result = V4L2FormatParser.parse_frameinterval(frameinterval_output)
        self.assertEqual(result, expected_result)

    def test_parse_frameinterval_invalid(self):
        """
        Test parsing of invalid or unexpected `ioctl: VIDIOC_ENUM_FRAMEINTERVALS` output.
        """
        frameinterval_output = "Invalid Output"
        result = V4L2FormatParser.parse_frameinterval(frameinterval_output)
        self.assertIsNone(result)

    @patch("app.util.v4l2_parser.subprocess.run")
    def test_get_fps_intervals_success(self, mock_subprocess_run: Mock):
        """
        Test `get_fps_intervals` retrieves and parses frame intervals successfully.
        """
        mock_subprocess_run.return_value.stdout = (
            "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\n"
            "        Interval: Discrete 0.033s (30.000 fps)\n"
            "        Interval: Discrete 0.067s (15.000 fps)"
        )

        expected_result = (15, 30)
        result = V4L2FormatParser.get_fps_intervals(
            self.device, width=640, height=480, pixel_format="YUYV"
        )
        self.assertEqual(result, expected_result)

    @patch("app.util.logger.Logger.error")
    @patch("app.util.v4l2_parser.subprocess.run")
    def test_get_fps_intervals_failure(
        self, mock_subprocess_run: Mock, mock_logger_error: Mock
    ):
        """
        Test `get_fps_intervals` handles subprocess errors gracefully.
        """
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "v4l2-ctl")
        result = V4L2FormatParser.get_fps_intervals(
            self.device, width=640, height=480, pixel_format="YUYV"
        )

        mock_logger_error.assert_called_once()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
