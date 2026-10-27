import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from app.adapters.hailo_adapter import YOLOHailoAdapter


class TestYOLOHailoAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = MagicMock()
        self.runtime.get_input_shape.return_value = (640, 640, 3)
        self.runtime.describe.return_value = ([], [("nms", (80, 5, 100), None)])
        module = MagicMock()
        module.Hailo.return_value = self.runtime
        patcher = patch.dict("sys.modules", {"picamera2.devices.hailo.hailo": module})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.adapter = YOLOHailoAdapter("model.hef", labels={0: "person"})

    def test_confidence_threshold_and_native_shape(self) -> None:
        self.runtime.run.return_value = [np.array([[0.25, 0.25, 0.75, 0.75, 0.3]])]
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        result = self.adapter.predict(frame, conf=0.2)[0]
        self.assertEqual(len(list(result.boxes)), 1)
        self.assertEqual(list(result.boxes)[0].xyxy.tolist(), [[160, 160, 480, 480]])
        self.assertEqual(list(self.adapter.predict(frame, conf=0.5)[0].boxes), [])

    def test_undoes_internal_letterbox_for_non_square_frame(self) -> None:
        self.runtime.run.return_value = [np.array([[0.25, 0.25, 0.75, 0.75, 0.9]])]
        result = self.adapter.predict(np.zeros((240, 320, 3), dtype=np.uint8))[0]
        self.assertEqual(self.runtime.run.call_args.args[0].shape, (640, 640, 3))
        self.assertEqual(list(result.boxes)[0].xyxy.tolist(), [[80, 40, 240, 200]])

    def test_close_releases_device_once(self) -> None:
        self.adapter.close()
        self.adapter.close()
        self.runtime.close.assert_called_once()

    def test_failed_metadata_initialization_releases_device(self) -> None:
        self.runtime.describe.side_effect = RuntimeError("invalid model metadata")
        with self.assertRaisesRegex(RuntimeError, "invalid model metadata"):
            YOLOHailoAdapter("invalid.hef")
        self.runtime.close.assert_called_once()

    @patch("app.util.pose_util.postproc_yolov8_pose")
    def test_pose_filters_padding_rows_and_restores_points(
        self, postprocess: MagicMock
    ) -> None:
        self.adapter.is_pose = True
        postprocess.return_value = {
            "bboxes": np.array([[[160, 160, 480, 480], [0, 0, 0, 0]]]),
            "scores": np.array([[[0.9], [0.0]]]),
            "keypoints": np.array([[[[160, 160]], [[0, 0]]]]),
            "joint_scores": np.array([[[[0.7]], [[0.0]]]]),
        }
        result = self.adapter.predict(
            np.zeros((240, 320, 3), dtype=np.uint8), conf=0.6
        )[0]
        self.assertEqual(len(list(result.boxes)), 1)
        self.assertEqual(list(result.boxes)[0].xyxy.tolist(), [[80, 40, 240, 200]])
        self.assertIsNotNone(result.keypoints)
        assert result.keypoints is not None
        np.testing.assert_allclose(result.keypoints.xy, [[[80, 40]]])
        assert result.keypoints.conf is not None
        np.testing.assert_allclose(result.keypoints.conf, [[0.7]])
        self.assertEqual(postprocess.call_args.kwargs["img_size"], (640, 640))
        self.assertEqual(postprocess.call_args.kwargs["confidence"], 0.6)
