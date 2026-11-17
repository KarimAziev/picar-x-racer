import asyncio
import threading
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from app.exceptions.detection import DetectionProcessError
from app.managers.detection.detection_process import detection_process_func
from app.schemas.detection import DetectionSettings
from app.services.detection.detection_service import DetectionService
from app.types.detection import DetectionQueueData, DetectionProcessOutput


class TestPhotoDetection(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        settings = MagicMock()
        settings.settings = {"detection": {"model": None}}
        profiles = MagicMock()
        profiles.selected_model = None
        self.service = DetectionService(settings, MagicMock(), MagicMock(), profiles)
        self.service.detection_settings = DetectionSettings.model_validate(
            {
                "active": True,
                "model": "yolo.pt",
                "img_size": 64,
                "confidence": 0.8,
                "labels": ["person"],
            }
        )
        self.process = MagicMock()
        self.process.is_alive.return_value = True
        self.service.detection_process = self.process
        self.frame = np.ones((60, 120, 3), dtype=np.uint8)

    def tearDown(self):
        for q in (
            self.service.frame_queue,
            self.service.detection_queue,
            self.service.control_queue,
            self.service.out_queue,
            self.service.photo_frame_queue,
            self.service.photo_result_queue,
        ):
            q.cancel_join_thread()
            q.close()

    async def test_matches_exact_request_without_changing_live_state(self):
        live: DetectionQueueData = {"detection_result": [], "timestamp": 1.0}
        self.service.detection_result = live
        task = asyncio.create_task(self.service.detect_photo(self.frame))
        request = await asyncio.to_thread(self.service.photo_frame_queue.get, True, 2)
        data = request["frame_data"]
        self.assertEqual((data["original_width"], data["original_height"]), (120, 60))
        self.assertEqual(data["frame"].shape[:2], (64, 64))
        self.assertEqual(
            (data["resized_width"], data["resized_height"], data["pad_top"]),
            (64, 32, 16),
        )
        self.assertEqual(request["confidence"], 0.8)
        self.assertEqual(request["labels"], ["person"])
        self.service.photo_result_queue.put({"request_id": "abandoned", "result": live})
        await asyncio.sleep(0.03)
        self.assertFalse(task.done())
        result: DetectionQueueData = {
            "detection_result": [],
            "timestamp": data["timestamp"],
        }
        self.service.photo_result_queue.put(
            {"request_id": request["request_id"], "result": result}
        )
        snapshot, detected = await asyncio.wait_for(task, 2)
        self.assertEqual(detected, result)
        self.assertIs(self.service.current_state, live)
        self.assertIsNot(snapshot, self.service.detection_settings)

    async def test_worker_error_is_propagated(self):
        task = asyncio.create_task(self.service.detect_photo(self.frame))
        request = await asyncio.to_thread(self.service.photo_frame_queue.get, True, 2)
        self.service.photo_result_queue.put(
            {"request_id": request["request_id"], "error": "Inference failed"}
        )
        with self.assertRaisesRegex(DetectionProcessError, "Inference failed"):
            await task

    async def test_timeout_releases_lifecycle_lock(self):
        self.service.PHOTO_TIMEOUT_SECONDS = 0.03
        with self.assertRaisesRegex(DetectionProcessError, "Timed out"):
            await self.service.detect_photo(self.frame)
        self.assertFalse(self.service.lock.locked())

    async def test_cancellation_allows_next_photo_and_ignores_late_result(self):
        task = asyncio.create_task(self.service.detect_photo(self.frame))
        abandoned = await asyncio.to_thread(self.service.photo_frame_queue.get, True, 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(self.service.lock.locked())
        self.service.photo_result_queue.put(
            {"request_id": abandoned["request_id"], "error": "Old failure"}
        )
        second = asyncio.create_task(self.service.detect_photo(self.frame))
        request = await asyncio.to_thread(self.service.photo_frame_queue.get, True, 2)
        await asyncio.sleep(0.03)
        self.service.photo_result_queue.put(
            {
                "request_id": request["request_id"],
                "result": {"detection_result": [], "timestamp": 5.0},
            }
        )
        _, result = await asyncio.wait_for(second, 2)
        self.assertEqual(result["timestamp"], 5.0)

    async def test_unavailable_worker_is_reported(self):
        self.process.is_alive.return_value = False
        with self.assertRaisesRegex(DetectionProcessError, "ready"):
            await self.service.detect_photo(self.frame)

    async def test_worker_handles_photo_failure_then_photo_and_live_results(self):
        output: DetectionProcessOutput = {
            "detection_result": [
                {"bbox": [10, 10, 40, 40], "label": "person", "confidence": 0.9}
            ],
            "semantic_mask": {
                "width": 2,
                "height": 1,
                "counts": [[0, 1], [1, 1]],
                "classes": {0: "background", 1: "person"},
            },
            "depth_map": {
                "width": 2,
                "height": 1,
                "data": "AP8=",
                "near": 0.0,
                "far": 1.0,
                "units": "relative",
            },
        }
        worker = threading.Thread(
            target=detection_process_func,
            args=(
                "yolo.pt",
                self.service.stop_event,
                self.service.frame_queue,
                self.service.detection_queue,
                self.service.control_queue,
                self.service.out_queue,
                self.service.photo_frame_queue,
                self.service.photo_result_queue,
            ),
        )
        with patch(
            "app.managers.detection.detection_process.ModelManager"
        ) as manager, patch(
            "app.managers.detection.detection_process.perform_detection",
            side_effect=[RuntimeError("Photo failed"), output, output],
        ) as infer:
            manager.return_value.__enter__.return_value = (
                MagicMock(names=["person"]),
                None,
            )
            worker.start()
            self.process.is_alive.side_effect = worker.is_alive
            try:
                with self.assertRaisesRegex(DetectionProcessError, "Photo failed"):
                    await self.service.detect_photo(self.frame)
                _, result = await self.service.detect_photo(self.frame)
                self.assertEqual(result.get("semantic_mask"), output["semantic_mask"])
                self.assertEqual(result.get("depth_map"), output["depth_map"])
                self.assertEqual(result["detection_result"], output["detection_result"])
                self.assertIsNone(self.service.detection_result)
                photo_args = infer.call_args.kwargs
                self.assertEqual(
                    (photo_args["original_width"], photo_args["original_height"]),
                    (120, 60),
                )
                self.assertEqual(photo_args["confidence_threshold"], 0.8)
                self.assertEqual(photo_args["labels_to_detect"], ["person"])
                self.service.put_frame(
                    {
                        "frame": self.frame,
                        "timestamp": 1.0,
                        "original_width": 120,
                        "original_height": 60,
                        "resized_width": 120,
                        "resized_height": 60,
                        "pad_left": 0,
                        "pad_top": 0,
                        "should_resize": False,
                    }
                )
                live = await asyncio.to_thread(
                    self.service.detection_queue.get, True, 2
                )
                self.assertEqual(live["timestamp"], 1.0)
                self.assertEqual(infer.call_args.kwargs["confidence_threshold"], 0.3)
                self.assertIsNone(infer.call_args.kwargs["labels_to_detect"])
            finally:
                self.service.stop_event.set()
                await asyncio.to_thread(worker.join, 2)
                self.assertFalse(worker.is_alive())
