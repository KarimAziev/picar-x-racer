from app.migrations.json_data import JsonDataMigrationError, JsonObject


def migrate_to_v3(data: JsonObject) -> JsonObject:
    """Add disabled motion control without guessing physical calibration."""

    motion_control = data.get("motion_control")
    if motion_control is None:
        data["motion_control"] = {"enabled": False}
    elif not isinstance(motion_control, dict):
        raise JsonDataMigrationError("'motion_control' must be an object or null")
    return data
