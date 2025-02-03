import os
import unittest
from typing import Any, Dict, cast
from unittest.mock import MagicMock, patch

from app.schemas.camera import DiscreteDevice
from app.services.v4l2_service import V4L2Service


class FakeFDContext:
    def __init__(self, fd: int = 3):
        self.fd = fd

    def __enter__(self):
        return self.fd

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def fake_fd_open(device_path: str, flags: int):
    return FakeFDContext(3)


class TestV4L2Service(unittest.TestCase):
    def setUp(self):
        V4L2Service._instances = {}
        self.service = V4L2Service()
        self.service._cached_list_video_devices.cache_clear()

    @patch("app.services.v4l2_service.os.listdir")
    def test_enumerate_video_devices(self, mock_listdir):
        mock_listdir.return_value = ["video2", "video3", "not_video", "video_dummy"]
        expected_devices = [
            os.path.join("/dev", "video2"),
            os.path.join("/dev", "video3"),
        ]
        devices = self.service._enumerate_video_devices()
        self.assertEqual(devices, expected_devices)

    @patch("app.services.v4l2_service.get_dev_video_checksum", return_value="dummy")
    def test_list_video_devices(self, _):
        with patch("app.services.v4l2_service.os.listdir") as mock_listdir, patch(
            "app.services.v4l2_service.V4L2Service._query_capabilities"
        ) as mock_query_capabilities, patch(
            "app.services.v4l2_service.V4L2Service._enumerate_formats",
            return_value=[
                {"index": 0, "pixelformat": 808596553, "description": "I420"}
            ],
        ), patch(
            "app.services.v4l2_service.V4L2Service._enumerate_framesizes",
            return_value=[{"type": "discrete", "width": 640, "height": 480}],
        ), patch(
            "app.services.v4l2_service.V4L2Service._enumerate_frameintervals",
            return_value=[{"type": "discrete", "fps": 30}],
        ):
            mock_listdir.return_value = ["video0", "video1", "not_video"]

            def query_side_effect(device):
                if device == "/dev/video0":
                    cap = MagicMock()
                    cap.capabilities = 0x00000001  # capture supported flag.
                    return cap
                return None

            mock_query_capabilities.side_effect = query_side_effect

            devices = self.service.list_video_devices()
            self.assertEqual(len(devices), 1)
            self.assertIn("/dev/video0", devices[0].device)

    @patch("fcntl.ioctl")
    @patch("app.services.v4l2_service.fd_open", new=fake_fd_open)
    def test_query_capabilities_success(self, mock_ioctl):
        mock_ioctl.side_effect = lambda fd, req, cap: cap if req == 0x80685600 else None
        result = self.service._query_capabilities("/dev/video10")
        self.assertIsNotNone(result)

    @patch("fcntl.ioctl", side_effect=OSError("IOCTL Failure"))
    @patch("app.services.v4l2_service.fd_open", new=fake_fd_open)
    def test_query_capabilities_failure(self, _):
        with patch("app.core.logger.Logger.warning") as mock_logger_warning:
            result = self.service._query_capabilities("/dev/video0")
            self.assertIsNone(result)
            mock_logger_warning.assert_called_once()

    @patch("app.services.v4l2_service.V4L2Service._enumerate_formats")
    @patch("app.services.v4l2_service.V4L2Service._enumerate_framesizes")
    @patch("app.services.v4l2_service.V4L2Service._enumerate_frameintervals")
    def test_get_device_configurations_discrete(
        self, mock_frameintervals, mock_framesizes, mock_formats
    ):

        mock_formats.return_value = [
            {"index": 0, "pixelformat": 808596553, "description": "I420"}
        ]
        mock_framesizes.return_value = [
            {"type": "discrete", "width": 640, "height": 480}
        ]
        mock_frameintervals.return_value = [
            {"type": "discrete", "fps": 30},
            {"type": "discrete", "fps": 60},
        ]
        result = self.service._get_device_configurations("/dev/video0")
        self.assertEqual(len(result), 2)
        discrete_device = result[0]
        self.assertIsInstance(discrete_device, DiscreteDevice)
        discrete_device = cast(DiscreteDevice, discrete_device)
        self.assertEqual(discrete_device.width, 640)
        self.assertEqual(discrete_device.height, 480)
        self.assertEqual(discrete_device.fps, 30)

    @patch("fcntl.ioctl")
    @patch("app.services.v4l2_service.fd_open", new=fake_fd_open)
    def test_video_capture_format_success(self, mock_ioctl):
        v4l2_format_mock = MagicMock()
        v4l2_format_mock.type = 1
        v4l2_format_mock.fmt.pix.width = 1920
        v4l2_format_mock.fmt.pix.height = 1080
        # 808596553 produces "I420"
        v4l2_format_mock.fmt.pix.pixelformat = 808596553

        # When ioctl is called with VIDIOC_G_FMT (0x806C5604), it returns the passed-in structure.
        mock_ioctl.side_effect = lambda fd, req, fmt: fmt if req == 0x806C5604 else None

        with patch(
            "app.services.v4l2_service.v4l2_format", return_value=v4l2_format_mock
        ):
            result = self.service.video_capture_format("/dev/video0")
            self.assertIsNotNone(result)
            result = cast(Dict[str, Any], result)
            self.assertEqual(result["width"], 1920)
            self.assertEqual(result["height"], 1080)
            self.assertEqual(result["pixel_format"], "I420")

    @patch("fcntl.ioctl", side_effect=OSError("IOCTL Failure"))
    @patch("app.services.v4l2_service.fd_open", new=fake_fd_open)
    def test_video_capture_format_failure(self, mock_ioctl):
        with patch("app.core.logger.Logger.error") as mock_logger_error:
            result = self.service.video_capture_format("/dev/video0")
            self.assertIsNone(result)
            mock_logger_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
