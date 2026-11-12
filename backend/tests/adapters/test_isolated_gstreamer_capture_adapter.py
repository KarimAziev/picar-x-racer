import multiprocessing
import os
import signal
import threading
import unittest
from multiprocessing.connection import Connection
from typing import Any
from unittest.mock import patch

import numpy as np
from app.adapters.isolated_gstreamer_capture_adapter import (
    IsolatedGStreamerCaptureAdapter,
)
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from app.services.camera.gstreamer_service import GStreamerService


def crash_worker(connection: Connection, device: str, settings: dict[str, Any]):
    os.kill(os.getpid(), signal.SIGKILL)


def frame_worker(connection: Connection, device: str, settings: dict[str, Any]):
    connection.send(("ready", (settings, np.ones((2, 2, 3), dtype=np.uint8))))
    while connection.recv() == "read":
        connection.send(("frame", np.full((2, 2, 3), 2, dtype=np.uint8)))
    connection.close()


def read_crash_worker(connection: Connection, device: str, settings: dict[str, Any]):
    connection.send(("ready", (settings, np.ones((2, 2, 3), dtype=np.uint8))))
    connection.recv()
    os.kill(os.getpid(), signal.SIGKILL)


def hung_worker(connection: Connection, device: str, settings: dict[str, Any]):
    threading.Event().wait()


class TestIsolatedGStreamerCapture(unittest.TestCase):
    def create_adapter(self):
        return IsolatedGStreamerCaptureAdapter(
            "libcamera:/test-camera",
            CameraSettings(pixel_format="NV12"),
            GStreamerService(),
        )

    def test_native_startup_crash_becomes_camera_error_and_reaps_worker(self):
        before = {p.pid for p in multiprocessing.active_children()}
        with patch(
            "app.adapters.isolated_gstreamer_capture_adapter._capture_worker",
            crash_worker,
        ):
            with self.assertRaisesRegex(CameraDeviceError, "SIGKILL"):
                self.create_adapter()
        self.assertEqual(before, {p.pid for p in multiprocessing.active_children()})

    def test_frames_cross_process_boundary_and_release_is_idempotent(self):
        with patch(
            "app.adapters.isolated_gstreamer_capture_adapter._capture_worker",
            frame_worker,
        ):
            adapter = self.create_adapter()
        try:
            self.assertEqual(adapter.settings.pixel_format, "NV12")
            ok, frame = adapter.read()
            self.assertTrue(ok)
            np.testing.assert_array_equal(frame, np.ones((2, 2, 3)))
            ok, frame = adapter.read()
            self.assertTrue(ok)
            np.testing.assert_array_equal(frame, np.full((2, 2, 3), 2))
        finally:
            adapter.release()
            adapter.release()

    def test_native_read_crash_becomes_camera_error(self):
        with patch(
            "app.adapters.isolated_gstreamer_capture_adapter._capture_worker",
            read_crash_worker,
        ):
            adapter = self.create_adapter()
        try:
            adapter.read()
            with self.assertRaisesRegex(CameraDeviceError, "SIGKILL"):
                adapter.read()
        finally:
            adapter.release()

    def test_hung_startup_times_out_and_terminates_worker(self):
        before = {p.pid for p in multiprocessing.active_children()}
        with patch(
            "app.adapters.isolated_gstreamer_capture_adapter._capture_worker",
            hung_worker,
        ), patch.object(IsolatedGStreamerCaptureAdapter, "START_TIMEOUT_SECONDS", 0.1):
            with self.assertRaisesRegex(CameraDeviceError, "timed out"):
                self.create_adapter()
        self.assertEqual(before, {p.pid for p in multiprocessing.active_children()})
