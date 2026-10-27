import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from app.adapters.gstreamer_capture_adapter import GStreamerCaptureAdapter
from app.services.camera.gstreamer_service import GStreamerService


class TestGStreamerCapture(unittest.TestCase):
    def test_libcamera_device_without_object_path(self):
        props = Mock()
        props.get_string.side_effect = lambda key: {
            "api.libcamera.Model": "imx708"
        }.get(key)
        self.assertEqual(
            GStreamerService.device_path(props, "/base/camera"),
            "libcamera:/base/camera",
        )
        props.get_string.side_effect = lambda key: {
            "object.path": "v4l2:/dev/video0"
        }.get(key)
        self.assertEqual(
            GStreamerService.device_path(props, "USB Camera"), "v4l2:/dev/video0"
        )

    def test_frame_owns_data_after_unmap_and_removes_row_padding(self):
        adapter = object.__new__(GStreamerCaptureAdapter)
        storage = bytearray([1, 2, 3, 4, 5, 6, 99, 99] * 2)
        buffer = Mock()
        buffer.map.return_value = (True, SimpleNamespace(data=storage))
        buffer.unmap.side_effect = lambda _: storage.__setitem__(slice(None), bytes(16))
        sample = Mock()
        sample.get_buffer.return_value = buffer
        sample.get_caps.return_value.get_structure.return_value.get_value.side_effect = {
            "width": 2,
            "height": 2,
        }.get
        adapter.appsink = Mock()
        adapter.appsink.emit.return_value = sample
        video = Mock()
        video.VideoInfo.new_from_caps.return_value = SimpleNamespace(
            stride=[8], offset=[0]
        )
        video.buffer_get_video_meta.return_value = None
        gst = Mock()
        gst.SECOND = 1000000000
        with patch.object(adapter, "Gst", gst, create=True), patch.object(
            adapter, "GstVideo", video, create=True
        ):
            ok, frame = adapter.read()
        self.assertTrue(ok)
        np.testing.assert_array_equal(frame, np.array([[[1, 2, 3], [4, 5, 6]]] * 2))
        adapter.appsink.emit.assert_called_once_with("try-pull-sample", 1000000000)
