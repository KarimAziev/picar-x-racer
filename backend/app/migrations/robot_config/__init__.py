from app.migrations.json_data import JsonDataMigrator, JsonObject
from app.migrations.robot_config.v1_motor_list import migrate_to_v1
from app.migrations.robot_config.v2_battery_list import migrate_to_v2
from app.migrations.robot_config.v3_motion_control import migrate_to_v3
from app.migrations.robot_config.v4_ackermann_odometry import migrate_to_v4
from app.migrations.robot_config.v5_localization_sensors import migrate_to_v5
from app.schemas.robot.config import HardwareConfig


def _validate_hardware_config(data: JsonObject) -> None:
    HardwareConfig.model_validate(data)


def create_robot_config_migrator() -> JsonDataMigrator:
    return JsonDataMigrator(
        {
            1: migrate_to_v1,
            2: migrate_to_v2,
            3: migrate_to_v3,
            4: migrate_to_v4,
            5: migrate_to_v5,
        },
        validator=_validate_hardware_config,
    )


__all__ = ["create_robot_config_migrator"]
