import json
import tempfile
import unittest
from pathlib import Path

from app.schemas.detection import DetectionModelSettings, OverlayStyle
from app.schemas.detection import DetectionSettings
from app.services.detection.detection_profile_service import (
    DetectionProfileService,
    infer_model_task,
)


class TestDetectionProfileService(unittest.TestCase):
    def make_service(self, temp_dir: str) -> DetectionProfileService:
        root = Path(temp_dir)
        template = root / "default.json"
        labels = root / "labels.txt"
        template.write_text(
            json.dumps({"schema_version": 2, "selected_model": None, "profiles": {}})
        )
        labels.write_text("person\ncar\n")
        return DetectionProfileService(
            target_file=str(root / "profiles.json"),
            template_file=str(template),
            labels_file=str(labels),
        )

    def test_infers_model_tasks_from_common_file_names(self) -> None:
        self.assertEqual(infer_model_task("yolo11n.pt").value, "detect")
        self.assertEqual(infer_model_task("yolo11n-pose.pt").value, "pose")
        self.assertEqual(infer_model_task("yolov8s_pose.hef").value, "pose")
        self.assertEqual(
            infer_model_task("yolo11n-seg.pt").value, "instance-segmentation"
        )
        self.assertEqual(
            infer_model_task("yolo26n-sem.pt").value, "semantic-segmentation"
        )

    def test_generates_task_appropriate_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)

            self.assertEqual(
                service.get_profile("yolo11n.pt").overlay_style, OverlayStyle.BOX
            )
            self.assertEqual(
                service.get_profile("yolo11n-pose.pt").overlay_style,
                OverlayStyle.POSE,
            )
            self.assertEqual(
                service.get_profile("yolo11n-seg.pt").overlay_style,
                OverlayStyle.BBOX_SEGMENT,
            )
            semantic = service.get_profile("yolo26n-sem.pt")
            self.assertEqual(semantic.overlay_style, OverlayStyle.SEMANTIC)
            self.assertEqual(semantic.available_labels, [])
            self.assertEqual(
                service.get_profile("yolo11n.pt").available_labels,
                ["person", "car"],
            )

    def test_bootstraps_legacy_model_with_task_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)

            service.bootstrap_legacy(
                DetectionSettings(
                    model="yolo26n-sem.pt", overlay_style=OverlayStyle.BOX
                )
            )

            profile = service.get_profile("yolo26n-sem.pt")
            self.assertEqual(profile.overlay_style, OverlayStyle.SEMANTIC)

    def test_restores_saved_settings_per_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self.make_service(temp_dir)
            pose = service.select_model("yolo11n-pose.pt")
            pose.keypoint_confidence_threshold = 0.15
            pose.confidence = 0.8
            pose.iou_threshold = 0.45
            pose.max_detections = 25
            service.save_profile("yolo11n-pose.pt", pose)

            service.select_model("yolo11n-seg.pt")
            restored = service.select_model("yolo11n-pose.pt")

            self.assertEqual(restored.confidence, 0.8)
            self.assertEqual(restored.keypoint_confidence_threshold, 0.15)
            self.assertEqual(restored.iou_threshold, 0.45)
            self.assertEqual(restored.max_detections, 25)

            reloaded = self.make_service(temp_dir)
            self.assertEqual(reloaded.selected_model, "yolo11n-pose.pt")
            self.assertEqual(
                reloaded.get_profile("yolo11n-pose.pt"),
                DetectionModelSettings.model_validate(restored.model_dump()),
            )


if __name__ == "__main__":
    unittest.main()
