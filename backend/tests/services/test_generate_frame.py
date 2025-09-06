import struct
import unittest
from typing import Optional, cast
from unittest.mock import patch

import cv2
import numpy as np
from app.exceptions.camera import CameraDeviceError
from app.schemas.stream import StreamSettings
from app.services.camera.camera_service import CameraService
from app.services.camera.stream_service import StreamService


class DummyCameraServiceWithProps:
    def __init__(self):
        self.shutting_down: bool = False
        self.camera_run: bool = False
        self.loading: bool = False
        self.camera_device_error: Optional[str] = None
        self.stream_img: Optional[np.ndarray] = None
        self.stream_settings = StreamSettings()

        self.current_frame_timestamp: Optional[float] = None
        self.actual_fps: Optional[float] = None

    def start_camera(self) -> None:
        pass


class TestGenerateFrame(unittest.TestCase):
    def setUp(self):
        self.dummy_cam = cast(CameraService, DummyCameraServiceWithProps())
        self.dummy_cam.stream_settings.format = ".jpg"
        self.dummy_cam.stream_settings.quality = 95
        self.dummy_cam.current_frame_timestamp = 123456789.0
        self.dummy_cam.actual_fps = 30.0
        self.dummy_cam.camera_device_error = None
        self.dummy_cam.shutting_down = False
        self.stream_service = StreamService(camera_service=self.dummy_cam)

    def tearDown(self):
        self.dummy_cam.camera_device_error = None
        self.dummy_cam.shutting_down = False

    def test_generate_frame_valid(self):
        """
        Test that generate_frame returns the correct bytes (timestamp, fps, encoded frame)
        when provided with a valid frame.
        """
        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        expected_encoded = b"ENCODED_FRAME"

        with patch(
            "app.services.camera.stream_service.encode", return_value=expected_encoded
        ) as mocked_encode:

            self.dummy_cam.camera_device_error = None
            result = self.stream_service._generate_frame(dummy_frame)
            expected_timestamp = struct.pack(
                "d", self.dummy_cam.current_frame_timestamp
            )
            expected_fps = struct.pack("d", self.dummy_cam.actual_fps)
            expected_result = expected_timestamp + expected_fps + expected_encoded
            self.assertEqual(result, expected_result)
            mocked_encode.assert_called_once_with(
                dummy_frame,
                self.dummy_cam.stream_settings.format,
                [cv2.IMWRITE_JPEG_QUALITY, self.dummy_cam.stream_settings.quality],
            )

    def test_generate_frame_camera_device_error(self):
        """
        Test that if a camera device error has been set, then generate_frame raises a
        CameraDeviceError with the correct message.
        """
        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        self.dummy_cam.shutting_down = False
        self.dummy_cam.camera_device_error = "Test camera error"
        with self.assertRaises(CameraDeviceError):
            self.stream_service._generate_frame(dummy_frame)


if __name__ == "__main__":
    unittest.main()
