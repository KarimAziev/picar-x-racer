from app.migrations.json_data import JsonDataMigrationError, JsonObject


def migrate_to_v5(data: JsonObject) -> JsonObject:
    """Add disabled localization features without guessing calibration."""

    sensors = data.get("localization_sensors")
    if sensors is None:
        data["localization_sensors"] = {
            "lidar": {"enabled": False},
            "imu": {"enabled": False},
            "encoder": {"enabled": False},
        }
    elif not isinstance(sensors, dict):
        raise JsonDataMigrationError("'localization_sensors' must be an object or null")

    for field_name in ("lidar_safety", "local_mapping"):
        value = data.get(field_name)
        if value is None:
            data[field_name] = {"enabled": False}
        elif not isinstance(value, dict):
            raise JsonDataMigrationError(f"'{field_name}' must be an object or null")
    return data
