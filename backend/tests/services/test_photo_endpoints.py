import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from app.api.endpoints.camera import take_photo
from app.exceptions.camera import CameraBusyError, CameraDeviceError
from app.exceptions.detection import DetectionProcessError
from app.schemas.detection import DetectionSettings, OverlayStyle
from app.schemas.photo import PhotoCameraSettings, PhotoCaptureRequest, PhotoPreset
from app.schemas.stream import ImageRotation, StreamSettings
from fastapi import HTTPException


class TestPhotoEndpoints(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.camera = MagicMock()
        self.camera.photo_capturing = False
        self.camera.stream_settings = StreamSettings()
        self.camera.stream_img = np.ones((3, 4, 3), dtype=np.uint8)
        self.camera.current_frame_timestamp = 10.0
        self.camera.capture_preset_photo = AsyncMock(
            return_value=np.ones((6, 8, 3), dtype=np.uint8)
        )
        self.preset = PhotoPreset(
            id="high",
            name="High",
            format=".png",
            rotation=ImageRotation.rotate_90,
            camera=PhotoCameraSettings(device="camera", width=8, height=6),
        )
        self.camera.file_manager.settings = {
            "photo": {"presets": [self.preset.model_dump()]}
        }
        self.detection = MagicMock()
        self.detection.detection_settings = DetectionSettings.model_validate(
            {"active": False}
        )
        self.files = MagicMock()
        self.files.root_directory = "/photos"
        writer = patch("app.api.endpoints.camera.capture_photo", new_callable=AsyncMock)
        self.writer = writer.start()
        self.writer.return_value = True
        self.addCleanup(writer.stop)

    async def test_preset_detects_captured_frame_and_rotates_overlay(self):
        self.detection.detection_settings.active = True
        self.detection.detection_settings.overlay_style = OverlayStyle.BOX
        captured = np.zeros((60, 80, 3), dtype=np.uint8)
        self.camera.capture_preset_photo.return_value = captured
        self.detection.detect_photo = AsyncMock(
            return_value=(
                self.detection.detection_settings,
                {
                    "detection_result": [
                        {"bbox": [10, 10, 30, 30], "label": "person", "confidence": 0.9}
                    ],
                    "timestamp": 20.0,
                },
            )
        )
        response = await take_photo(
            self.camera,
            self.detection,
            self.files,
            PhotoCaptureRequest(preset_id="high"),
        )
        self.assertTrue(response["file"].endswith(".png"))
        self.camera.capture_preset_photo.assert_awaited_once_with(self.preset)
        self.detection.poll_detection_result.assert_not_called()
        self.detection.detect_photo.assert_awaited_once()
        self.assertIs(self.detection.detect_photo.call_args.args[0], captured)
        saved = self.writer.call_args.kwargs["img"]
        self.assertEqual(saved.shape, (80, 60, 3))
        self.assertGreater(int(saved.sum()), 0)
        self.assertEqual(int(captured.sum()), 0)
        self.assertEqual(self.writer.call_args.kwargs["quality"], 95)

    async def test_empty_request_preserves_stream_snapshot(self):
        await take_photo(self.camera, self.detection, self.files)
        self.camera.capture_preset_photo.assert_not_awaited()
        self.assertEqual(self.writer.call_args.kwargs["img"].shape, (3, 4, 3))

    async def test_disabled_detection_or_media_overlay_skips_inference(self):
        self.detection.detect_photo = AsyncMock()
        for active, overlay in [(False, True), (True, False)]:
            with self.subTest(active=active, overlay=overlay):
                self.detection.detection_settings.active = active
                self.camera.stream_settings.include_detection_overlay_in_media = overlay
                await take_photo(
                    self.camera,
                    self.detection,
                    self.files,
                    PhotoCaptureRequest(preset_id="high"),
                )
        self.detection.detect_photo.assert_not_awaited()
        self.assertEqual(self.writer.await_count, 2)

    async def test_photo_inference_failure_does_not_save_unannotated_photo(self):
        self.detection.detection_settings.active = True
        self.detection.detect_photo = AsyncMock(
            side_effect=DetectionProcessError("Inference failed")
        )
        with self.assertRaises(HTTPException) as error:
            await take_photo(
                self.camera,
                self.detection,
                self.files,
                PhotoCaptureRequest(preset_id="high"),
            )
        self.assertEqual(error.exception.status_code, 503)
        self.assertIn("Inference failed", error.exception.detail)
        self.writer.assert_not_awaited()

    async def test_unknown_preset_does_not_capture(self):
        with self.assertRaises(HTTPException) as error:
            await take_photo(
                self.camera,
                self.detection,
                self.files,
                PhotoCaptureRequest(preset_id="missing"),
            )
        self.assertEqual(error.exception.status_code, 404)
        self.camera.capture_preset_photo.assert_not_awaited()
        self.writer.assert_not_awaited()

    async def test_camera_errors_have_actionable_statuses(self):
        for exception, status in [
            (CameraBusyError("recording"), 409),
            (CameraDeviceError("resolution"), 400),
        ]:
            self.camera.capture_preset_photo.side_effect = exception
            with self.assertRaises(HTTPException) as error:
                await take_photo(
                    self.camera,
                    self.detection,
                    self.files,
                    PhotoCaptureRequest(preset_id="high"),
                )
            self.assertEqual(error.exception.status_code, status)
        self.writer.assert_not_awaited()

    async def test_save_failure_is_reported_after_capture_completes(self):
        self.writer.return_value = False
        with self.assertRaises(HTTPException) as error:
            await take_photo(
                self.camera,
                self.detection,
                self.files,
                PhotoCaptureRequest(preset_id="high"),
            )
        self.assertEqual(error.exception.detail, "Error saving photo")
        self.camera.capture_preset_photo.assert_awaited_once()

    async def test_names_do_not_collide_for_rapid_snapshots(self):
        first = await take_photo(self.camera, self.detection, self.files)
        second = await take_photo(self.camera, self.detection, self.files)
        self.assertNotEqual(first["file"], second["file"])
