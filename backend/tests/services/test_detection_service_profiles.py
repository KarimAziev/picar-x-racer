import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from app.schemas.detection import DetectionSettings, OverlayStyle
from app.services.connection_service import ConnectionService
from app.services.detection.detection_profile_service import DetectionProfileService
from app.services.detection.detection_service import DetectionService
from app.services.domain.settings_service import SettingsService
from app.services.file_management.file_manager_service import FileManagerService


class DummySettingsService(SettingsService):
    def __init__(self) -> None:
        self.settings: dict[str, Any] = {"detection": {}}


class DummyFileManager(FileManagerService):
    def __init__(self) -> None:
        self.root_directory = ""


class DummyConnectionService(ConnectionService):
    def __init__(self) -> None:
        super().__init__()


class TestDetectionServiceProfiles(unittest.IsolatedAsyncioTestCase):
    async def test_model_switch_loads_and_restores_the_model_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            template = root / "default.json"
            template.write_text(
                json.dumps(
                    {"schema_version": 2, "selected_model": None, "profiles": {}}
                )
            )
            profile_service = DetectionProfileService(
                target_file=str(root / "profiles.json"),
                template_file=str(template),
                labels_file=None,
            )
            service = DetectionService(
                settings_service=DummySettingsService(),
                file_manager=DummyFileManager(),
                connection_manager=DummyConnectionService(),
                profile_service=profile_service,
            )
            try:
                pose = await service.update_detection_settings(
                    DetectionSettings(
                        model="yolo11n-pose.pt",
                        confidence=0.9,
                        overlay_style=OverlayStyle.BOX,
                    )
                )
                self.assertEqual(pose.confidence, 0.4)
                self.assertEqual(pose.overlay_style, OverlayStyle.POSE)

                pose.confidence = 0.8
                pose.iou_threshold = 0.45
                pose.max_detections = 25
                pose.keypoint_confidence_threshold = 0.15
                await service.update_detection_settings(pose)

                segmentation = await service.update_detection_settings(
                    DetectionSettings(
                        **pose.model_dump(exclude={"model"}),
                        model="yolo11n-seg.pt",
                    )
                )
                self.assertEqual(segmentation.confidence, 0.4)
                self.assertEqual(segmentation.overlay_style, OverlayStyle.BBOX_SEGMENT)

                restored = await service.update_detection_settings(
                    DetectionSettings(
                        **segmentation.model_dump(exclude={"model"}),
                        model="yolo11n-pose.pt",
                    )
                )
                self.assertEqual(restored.confidence, 0.8)
                self.assertEqual(restored.iou_threshold, 0.45)
                self.assertEqual(restored.max_detections, 25)
                self.assertEqual(restored.keypoint_confidence_threshold, 0.15)
            finally:
                for process_queue in (
                    service.frame_queue,
                    service.detection_queue,
                    service.control_queue,
                    service.out_queue,
                ):
                    process_queue.close()
                    process_queue.cancel_join_thread()


if __name__ == "__main__":
    unittest.main()
