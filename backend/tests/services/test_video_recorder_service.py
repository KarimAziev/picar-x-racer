import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from unittest.mock import MagicMock, patch

import numpy as np

from app.services.file_management.file_manager_service import FileManagerService
from app.services.media.video_recorder_service import VideoRecorderService


class TestVideoRecorderService(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        manager = MagicMock(spec=FileManagerService)
        manager.root_directory = directory.name
        self.recorder = VideoRecorderService(manager)
        self.frame = np.zeros((24, 32, 3), dtype=np.uint8)

    def test_stop_waits_for_in_flight_frame_and_ignores_later_frames(self) -> None:
        entered = threading.Event()
        finish = threading.Event()

        def write(_frame: np.ndarray) -> None:
            entered.set()
            if not finish.wait(3):
                raise TimeoutError("Frame write was not released")

        writer = MagicMock()
        writer.write.side_effect = write
        with patch(
            "app.services.media.video_recorder_service.cv2.VideoWriter",
            return_value=writer,
        ):
            self.recorder.start_recording(32, 24, 30)
        with ThreadPoolExecutor(max_workers=2) as pool:
            writing = pool.submit(self.recorder.write_frame, self.frame)
            self.assertTrue(entered.wait(2))
            stopping = pool.submit(self.recorder.stop_recording)
            try:
                with self.assertRaises(TimeoutError):
                    stopping.result(timeout=0.05)
                writer.release.assert_not_called()
            finally:
                finish.set()
            writing.result(timeout=2)
            stopping.result(timeout=2)
        self.recorder.write_frame(self.frame)
        self.recorder.stop_recording()
        writer.write.assert_called_once()
        writer.release.assert_called_once()
        self.assertIsNone(self.recorder.video_writer)

    def test_start_releases_existing_writer_before_opening_another(self) -> None:
        first = MagicMock()
        second = MagicMock()
        with patch(
            "app.services.media.video_recorder_service.cv2.VideoWriter",
            side_effect=[first, second],
        ) as factory:
            self.recorder.start_recording(32, 24, 30)
            self.recorder.start_recording(32, 24, 30)
            self.assertEqual(factory.call_count, 2)
        first.release.assert_called_once()
        self.recorder.write_frame(self.frame)
        second.write.assert_called_once()
        self.recorder.stop_recording()
        second.release.assert_called_once()

    def test_failed_open_is_released_and_reported(self) -> None:
        writer = MagicMock()
        writer.isOpened.return_value = False
        with patch(
            "app.services.media.video_recorder_service.cv2.VideoWriter",
            return_value=writer,
        ):
            with self.assertRaisesRegex(RuntimeError, "open video writer"):
                self.recorder.start_recording(32, 24, 30)
        writer.release.assert_called_once()
        self.assertIsNone(self.recorder.video_writer)
        self.assertIsNone(self.recorder.current_video_path)

    def test_failed_release_detaches_writer(self) -> None:
        writer = MagicMock()
        writer.release.side_effect = RuntimeError("flush failed")
        with patch(
            "app.services.media.video_recorder_service.cv2.VideoWriter",
            return_value=writer,
        ):
            self.recorder.start_recording(32, 24, 30)
        self.recorder.stop_recording_safe()
        self.recorder.write_frame(self.frame)
        self.recorder.stop_recording_safe()
        writer.release.assert_called_once()
        writer.write.assert_not_called()
        self.assertIsNone(self.recorder.video_writer)
