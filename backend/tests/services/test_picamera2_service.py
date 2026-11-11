import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

from app.services.camera.picamera2_service import PicameraService


class TestPicameraService(unittest.TestCase):
    def test_concurrent_discovery_probes_each_camera_once(self):
        service = PicameraService()
        self.addCleanup(service._list_video_devices.cache_clear)
        camera_class = MagicMock()
        camera_class.global_camera_info.return_value = [
            {"Id": "/camera", "Num": 0, "Model": "imx708"}
        ]
        camera_class.return_value.sensor_modes = [{"size": (4608, 2592), "fps": 30}]
        entered = threading.Event()
        resume = threading.Event()

        def pause_probe(_):
            entered.set()
            if not resume.wait(2):
                raise AssertionError("Probe was not resumed")

        with patch(
            "app.services.camera.picamera2_service._load_picamera2_class",
            return_value=camera_class,
        ), patch(
            "app.services.camera.picamera2_service.time.sleep", side_effect=pause_probe
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(service.list_video_devices)
                self.assertTrue(entered.wait(2))
                second = executor.submit(service.list_video_devices)
                resume.set()
                self.assertEqual(first.result(), second.result())
        self.assertEqual(camera_class.call_count, 1)
        self.assertEqual(camera_class.global_camera_info.call_count, 1)
