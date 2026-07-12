from app.migrations.json_data import JsonDataMigrator, JsonObject
from app.migrations.robot_config.v1_motor_list import migrate_to_v1
from app.schemas.robot.config import HardwareConfig


def _validate_hardware_config(data: JsonObject) -> None:
    HardwareConfig.model_validate(data)


def create_robot_config_migrator() -> JsonDataMigrator:
    return JsonDataMigrator(
        {1: migrate_to_v1},
        validator=_validate_hardware_config,
    )


__all__ = ["create_robot_config_migrator"]
