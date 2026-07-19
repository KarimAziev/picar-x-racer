import os
import re
from typing import Any, Dict, List, Optional

from app.config.config import settings as app_config
from app.managers.file_management.json_data_manager import JsonDataManager
from app.migrations.detection_profiles import create_detection_profiles_migrator
from app.schemas.detection import (
    DetectionModelSettings,
    DetectionModelTask,
    DetectionProfilesConfig,
    DetectionSettings,
    OverlayStyle,
)


def infer_model_task(model: str) -> DetectionModelTask:
    name = os.path.basename(model).lower()
    if re.search(r"(?:^|[-_.])pose(?:[-_.]|$)", name):
        return DetectionModelTask.POSE
    if re.search(r"(?:^|[-_.])sem(?:[-_.]|$)", name):
        return DetectionModelTask.SEMANTIC_SEGMENTATION
    if re.search(r"(?:^|[-_.])seg(?:[-_.]|$)", name):
        return DetectionModelTask.INSTANCE_SEGMENTATION
    return DetectionModelTask.DETECT


class DetectionProfileService:
    """Resolve task defaults and persist user overrides per model."""

    def __init__(
        self,
        target_file: str = app_config.DETECTION_PROFILES_FILE,
        template_file: str = app_config.DEFAULT_DETECTION_PROFILES,
        labels_file: Optional[str] = app_config.HAILO_LABELS,
    ) -> None:
        self._manager = JsonDataManager(
            target_file=target_file,
            template_file=template_file,
            migrator=create_detection_profiles_migrator(),
        )
        self._labels = self._load_labels(labels_file)
        self._config = DetectionProfilesConfig.model_validate(self._manager.load_data())

    @staticmethod
    def _load_labels(labels_file: Optional[str]) -> List[str]:
        if not labels_file or not os.path.isfile(labels_file):
            return []
        with open(labels_file, "r", encoding="utf-8") as stream:
            return [line.strip() for line in stream if line.strip()]

    @property
    def selected_model(self) -> Optional[str]:
        return self._config.selected_model

    def default_profile(self, model: str) -> DetectionModelSettings:
        task = infer_model_task(model)
        style_by_task = {
            DetectionModelTask.DETECT: OverlayStyle.BOX,
            DetectionModelTask.POSE: OverlayStyle.POSE,
            DetectionModelTask.INSTANCE_SEGMENTATION: OverlayStyle.BBOX_SEGMENT,
            DetectionModelTask.SEMANTIC_SEGMENTATION: OverlayStyle.SEMANTIC,
        }
        return DetectionModelSettings(
            overlay_style=style_by_task[task],
            available_labels=self._default_labels_for(model),
        )

    def _default_labels_for(self, model: str) -> List[str]:
        name = os.path.basename(model).lower()
        if infer_model_task(model) == DetectionModelTask.SEMANTIC_SEGMENTATION:
            return []
        if any(marker in name for marker in ("-oiv7", "world", "yoloe-")):
            return []
        return list(self._labels)

    def get_profile(self, model: str) -> DetectionModelSettings:
        defaults = self.default_profile(model).model_dump(mode="json")
        saved = self._config.profiles.get(model)
        if saved is not None:
            defaults.update(saved.model_dump(mode="json"))
        return DetectionModelSettings.model_validate(defaults)

    def select_model(self, model: str) -> DetectionModelSettings:
        profile = self.get_profile(model)
        self._config.selected_model = model
        if model not in self._config.profiles:
            self._config.profiles[model] = profile
        self._save()
        return profile

    def save_profile(
        self, model: str, settings: DetectionModelSettings
    ) -> DetectionModelSettings:
        self._config.selected_model = model
        self._config.profiles[model] = settings
        self._save()
        return settings

    def cache_available_labels(self, model: str, labels: List[str]) -> None:
        if not labels:
            return
        profile = self.get_profile(model)
        profile.available_labels = labels
        self.save_profile(model, profile)

    def bootstrap_legacy(self, settings: DetectionSettings) -> None:
        if not settings.model or self._config.selected_model is not None:
            return
        profile_data: Dict[str, Any] = settings.model_dump(
            mode="json", exclude={"model", "active"}
        )
        defaults = self.default_profile(settings.model)
        if settings.overlay_style == OverlayStyle.BOX:
            profile_data["overlay_style"] = defaults.overlay_style.value
        if not settings.available_labels:
            profile_data["available_labels"] = defaults.available_labels
        self.save_profile(
            settings.model,
            DetectionModelSettings.model_validate(profile_data),
        )

    def _save(self) -> None:
        data = self._manager.update(self._config.model_dump(mode="json"))
        self._config = DetectionProfilesConfig.model_validate(data)
