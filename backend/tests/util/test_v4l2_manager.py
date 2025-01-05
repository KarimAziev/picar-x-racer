import subprocess
import unittest
from unittest.mock import Mock, patch

from app.util.v4l2_manager import V4L2


class TestV4L2Manager(unittest.TestCase):
    def setUp(self):
        pass

    @patch("app.util.v4l2_manager.V4L2.v4l2_list_devices")
    def test_list_camera_devices(self, mock_v4l2_list_devices: Mock):
        """
        Test that `list_camera_devices` properly parses device categories and paths.
        """
        mock_v4l2_list_devices.return_value = [
            'Integrated Camera: Integrated C (usb-0000:00:14.0-8):',
            '\t/dev/video0',
            '\t/dev/video1',
            '\t/dev/video2',
            '\t/dev/video3',
            '\t/dev/media0',
            '\t/dev/media1',
        ]

        expected_result = [
            ('/dev/video0', 'Integrated Camera: Integrated C'),
            ('/dev/video1', 'Integrated Camera: Integrated C'),
            ('/dev/video2', 'Integrated Camera: Integrated C'),
            ('/dev/video3', 'Integrated Camera: Integrated C'),
        ]

        result = V4L2.list_camera_devices()
        self.assertEqual(result, expected_result)

    @patch("app.util.v4l2_manager.V4L2.v4l2_list_devices")
    @patch("os.listdir")
    def test_list_camera_devices_fallback(
        self, mock_listdir: Mock, mock_v4l2_list_devices: Mock
    ):
        """
        Test that `list_camera_devices` falls back to `/dev` parsing when no devices are found.
        """
        mock_v4l2_list_devices.return_value = []
        mock_listdir.return_value = ["video0", "video1"]

        expected_result = [
            ("/dev/video0", ""),
            ("/dev/video1", ""),
        ]

        result = V4L2.list_camera_devices()
        self.assertEqual(result, expected_result)

    @patch("app.util.v4l2_manager.V4L2.list_camera_devices")
    @patch("app.util.v4l2_manager.V4L2.list_device_formats_ext")
    def test_list_video_devices_with_formats(
        self, mock_list_formats: Mock, mock_list_devices: Mock
    ):
        """
        Test `list_video_devices_with_formats` returns devices with formats.
        """
        mock_list_devices.return_value = [
            ("/dev/video0", "Integrated Camera"),
            ("/dev/video1", None),
        ]
        mock_list_formats.side_effect = [
            [
                {
                    "key": "/dev/video0:MJPG",
                    "label": "MJPG",
                    "children": [
                        {
                            "device": "/dev/video0",
                            "width": 1920,
                            "height": 1080,
                            "pixel_format": "MJPG",
                            "key": "/dev/video0:MJPG:1920x1080:30",
                            "label": "MJPG, 1920x1080, 30 fps",
                            "fps": 30,
                        }
                    ],
                }
            ],
            [],
        ]

        expected_result = [
            {
                "key": "/dev/video0",
                "label": "/dev/video0 (Integrated Camera)",
                "children": [
                    {
                        "key": "/dev/video0:MJPG",
                        "label": "MJPG",
                        "children": [
                            {
                                "device": "/dev/video0",
                                "width": 1920,
                                "height": 1080,
                                "pixel_format": "MJPG",
                                "key": "/dev/video0:MJPG:1920x1080:30",
                                "label": "MJPG, 1920x1080, 30 fps",
                                "fps": 30,
                            }
                        ],
                    }
                ],
            }
        ]

        results = V4L2.list_video_devices_with_formats()
        self.assertEqual(results, expected_result)

    @patch("app.util.v4l2_manager.subprocess.run")
    def test_v4l2_list_devices_success(self, mock_run: Mock):
        """
        Test `v4l2_list_devices` successfully retrieves device listing.
        """
        mock_run.return_value.stdout = (
            "Integrated Camera: Integrated C:\n" "\t/dev/video0\n" "\t/dev/video1\n"
        )

        expected_result = [
            "Integrated Camera: Integrated C:",
            "\t/dev/video0",
            "\t/dev/video1",
        ]

        result = V4L2.v4l2_list_devices()
        self.assertEqual(result, expected_result)

    @patch("app.util.logger.Logger.error")
    @patch("app.util.v4l2_manager.subprocess.run")
    def test_v4l2_list_devices_failure(self, mock_run: Mock, mock_logger_error: Mock):
        """
        Test `v4l2_list_devices` gracefully handles subprocess errors.
        """
        mock_run.side_effect = subprocess.CalledProcessError(1, "v4l2-ctl")

        result = V4L2.v4l2_list_devices()
        self.assertEqual(result, [])
        mock_logger_error.assert_called_once()

    @patch("app.util.v4l2_manager.subprocess.run")
    def test_list_device_formats_ext(self, mock_run: Mock):
        """
        Test `list_device_formats_ext` retrieves and parses device formats.
        """
        mock_run.return_value.stdout = "Some sample V4L2-CTL output"

        with patch("app.util.v4l2_manager.V4L2FormatParser.parse") as mock_parse:
            mock_parse.return_value = [
                {
                    "key": "/dev/video0:MJPG",
                    "label": "MJPG",
                    "children": [],
                }
            ]

            result = V4L2.list_device_formats_ext("/dev/video0")
            self.assertEqual(
                result, [{"key": "/dev/video0:MJPG", "label": "MJPG", "children": []}]
            )

            mock_parse.assert_called_once_with("Some sample V4L2-CTL output")

    @patch("app.util.logger.Logger.error")
    @patch("app.util.v4l2_manager.subprocess.run")
    def test_list_device_formats_ext_failure(
        self, mock_run: Mock, mock_logger_error: Mock
    ):
        """
        Test `list_device_formats_ext` handles subprocess errors gracefully.
        """
        mock_run.side_effect = subprocess.CalledProcessError(1, "v4l2-ctl")

        result = V4L2.list_device_formats_ext("/dev/video0")
        self.assertEqual(result, [])
        mock_logger_error.assert_called_once()

    @patch("app.util.v4l2_manager.V4L2.list_camera_devices")
    def test_find_device_info_success(self, mock_list_devices: Mock):
        """
        Test `find_device_info` with a valid device.
        """
        mock_list_devices.return_value = [
            ("/dev/video0", "Integrated Camera"),
            ("/dev/video1", None),
        ]

        result = V4L2.find_device_info("/dev/video0")
        self.assertEqual(result, ("/dev/video0", "Integrated Camera"))

    @patch("app.util.v4l2_manager.V4L2.list_camera_devices")
    def test_find_device_info_failure(self, mock_list_devices: Mock):
        """
        Test `find_device_info` when device is not found.
        """
        mock_list_devices.return_value = [
            ("/dev/video0", "Integrated Camera"),
            ("/dev/video1", None),
        ]

        result = V4L2.find_device_info("/dev/video2")
        self.assertIsNone(result)

    @patch("app.util.v4l2_manager.subprocess.run")
    def test_video_capture_format_success(self, mock_run: Mock):
        """
        Test `video_capture_format` retrieves device format successfully.
        """
        mock_run.return_value.stdout = (
            "Format Video Capture:\n"
            "    Width/Height      : 800/600\n"
            "    Pixel Format      : 'MJPG' (Motion-JPEG)\n"
        )

        result = V4L2.video_capture_format("/dev/video0")
        self.assertEqual(result, {"width": 800, "height": 600, "pixel_format": "MJPG"})

    @patch("app.util.logger.Logger.error")
    @patch("app.util.v4l2_manager.subprocess.run")
    def test_video_capture_format_failure(
        self, mock_run: Mock, mock_logger_error: Mock
    ):
        """
        Test `video_capture_format` handles subprocess errors.
        """
        mock_run.side_effect = subprocess.CalledProcessError(1, "v4l2-ctl")

        result = V4L2.video_capture_format("/dev/video0")
        self.assertEqual(result, {})
        mock_logger_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
