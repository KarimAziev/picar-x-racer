from app.migrations.detection_profiles.v1_model_profiles import migrate_to_v1
from app.migrations.detection_profiles.v2_nms_settings import migrate_to_v2
from app.migrations.json_data import JsonDataMigrator, JsonObject
from app.schemas.detection import DetectionProfilesConfig


def _validate_detection_profiles(data: JsonObject) -> None:
    DetectionProfilesConfig.model_validate(data)


def create_detection_profiles_migrator() -> JsonDataMigrator:
    return JsonDataMigrator(
        {1: migrate_to_v1, 2: migrate_to_v2},
        validator=_validate_detection_profiles,
    )


__all__ = ["create_detection_profiles_migrator"]
