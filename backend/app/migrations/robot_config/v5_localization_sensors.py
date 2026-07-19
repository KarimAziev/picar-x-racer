from app.migrations.json_data import JsonDataMigrationError, JsonObject


def migrate_to_v5(data: JsonObject) -> JsonObject:
    """Add disabled localization sensors without guessing hardware calibration."""

    sensors = data.get("localization_sensors")
    if sensors is None:
        data["localization_sensors"] = {
            "lidar": {"enabled": False},
            "imu": {"enabled": False},
            "encoder": {"enabled": False},
        }
    elif not isinstance(sensors, dict):
        raise JsonDataMigrationError("'localization_sensors' must be an object or null")
    return data
