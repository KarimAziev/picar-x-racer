import unittest
from unittest.mock import MagicMock

from app.adapters.video_device_adapter import VideoDeviceAdapter
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.schemas.camera import DeviceStepwise, DiscreteDevice
from app.schemas.photo import PhotoCameraSettings


class TestPhotoModes(unittest.TestCase):
    def setUp(self):
        self.adapter = VideoDeviceAdapter(
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        self.devices = MagicMock(
            return_value=[
                DiscreteDevice(
                    name="USB",
                    device="v4l2:/dev/video0",
                    api="v4l2",
                    width=1920,
                    height=1080,
                    fps=15,
                    pixel_format="MJPG",
                )
            ]
        )
        self.adapter.list_devices = self.devices

    def test_accepts_supported_discrete_mode(self):
        self.adapter.validate_photo_settings(
            PhotoCameraSettings(
                device="v4l2:/dev/video0",
                width=1920,
                height=1080,
                fps=15,
                pixel_format="MJPG",
            )
        )

    def test_rejects_missing_camera_and_unsupported_modes(self):
        with self.assertRaises(CameraNotFoundError):
            self.adapter.validate_photo_settings(
                PhotoCameraSettings(device="missing", width=1920, height=1080)
            )
        for settings in [
            PhotoCameraSettings(device="v4l2:/dev/video0", width=3840, height=2160),
            PhotoCameraSettings(
                device="v4l2:/dev/video0", width=1920, height=1080, fps=30
            ),
            PhotoCameraSettings(
                device="v4l2:/dev/video0", width=1920, height=1080, pixel_format="YUYV"
            ),
        ]:
            with self.assertRaises(CameraDeviceError):
                self.adapter.validate_photo_settings(settings)

    def test_checks_stepwise_dimensions(self):
        self.devices.return_value = [
            DeviceStepwise(
                name="Front",
                pixel_format=None,
                fps_step=1,
                device="picamera2:/camera",
                api="picamera2",
                min_width=320,
                max_width=4608,
                min_height=240,
                max_height=2592,
                width_step=2,
                height_step=2,
                min_fps=1,
                max_fps=60,
            )
        ]
        self.adapter.validate_photo_settings(
            PhotoCameraSettings(device="picamera2:/camera", width=4608, height=2592)
        )
        with self.assertRaises(CameraDeviceError):
            self.adapter.validate_photo_settings(
                PhotoCameraSettings(device="picamera2:/camera", width=4607, height=2592)
            )
