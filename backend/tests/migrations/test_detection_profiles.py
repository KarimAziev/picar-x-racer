import json
import tempfile
import unittest
from pathlib import Path

from app.managers.file_management.json_data_manager import JsonDataManager
from app.migrations.detection_profiles import create_detection_profiles_migrator
from app.migrations.json_data import JsonDataMigrationError


class TestDetectionProfilesMigration(unittest.TestCase):
    def test_migrates_flat_settings_to_selected_model_profile(self) -> None:
        result = create_detection_profiles_migrator().migrate(
            {
                "model": "yolo11n-pose.pt",
                "active": True,
                "confidence": 0.6,
                "iou_threshold": 0.45,
                "max_detections": 50,
                "overlay_style": "pose",
                "keypoint_confidence_threshold": 0.05,
            }
        )

        self.assertEqual(result.applied_versions, (1, 2))
        self.assertEqual(result.data["schema_version"], 2)
        self.assertEqual(result.data["selected_model"], "yolo11n-pose.pt")
        self.assertEqual(result.data["profiles"]["yolo11n-pose.pt"]["confidence"], 0.6)
        self.assertEqual(
            result.data["profiles"]["yolo11n-pose.pt"]["iou_threshold"], 0.45
        )
        self.assertEqual(
            result.data["profiles"]["yolo11n-pose.pt"]["max_detections"], 50
        )
        self.assertNotIn("active", result.data)
        self.assertNotIn("model", result.data)

    def test_rejects_invalid_profile_collection(self) -> None:
        with self.assertRaisesRegex(JsonDataMigrationError, "must be an object"):
            create_detection_profiles_migrator().migrate({"profiles": []})

    def test_migrates_v1_profiles_with_nms_defaults(self) -> None:
        result = create_detection_profiles_migrator().migrate(
            {
                "schema_version": 1,
                "selected_model": "yolo11n.pt",
                "profiles": {
                    "yolo11n.pt": {"confidence": 0.5},
                    "yolo11n-pose.pt": {"confidence": 0.6},
                },
            }
        )

        self.assertEqual(result.applied_versions, (2,))
        for profile in result.data["profiles"].values():
            self.assertEqual(profile["iou_threshold"], 0.7)
            self.assertEqual(profile["max_detections"], 5)

    def test_manager_persists_migrated_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "profiles.json"
            template = Path(temp_dir) / "default.json"
            target.write_text(
                json.dumps({"model": "yolo11n-seg.pt", "confidence": 0.7})
            )
            template.write_text(
                json.dumps(
                    {"schema_version": 2, "selected_model": None, "profiles": {}}
                )
            )

            manager = JsonDataManager(
                str(target),
                str(template),
                migrator=create_detection_profiles_migrator(),
            )

            persisted = json.loads(target.read_text())
            self.assertEqual(manager.load_data(), persisted)
            self.assertEqual(persisted["schema_version"], 2)
            self.assertIn("yolo11n-seg.pt", persisted["profiles"])


if __name__ == "__main__":
    unittest.main()
