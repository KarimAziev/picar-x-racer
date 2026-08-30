from app.migrations.json_data import JsonDataMigrationError, JsonObject


def migrate_to_v6(data: JsonObject) -> JsonObject:
    """Add explicit drive-encoder devices and optional steering feedback."""

    localization = data.get("localization_sensors")
    if not isinstance(localization, dict):
        raise JsonDataMigrationError("'localization_sensors' must be an object")
    for sensor_name, default_driver in (("lidar", "rplidar_c1"), ("imu", "sh3001")):
        sensor = localization.get(sensor_name)
        if not isinstance(sensor, dict):
            raise JsonDataMigrationError(
                f"'localization_sensors.{sensor_name}' must be an object"
            )
        sensor.setdefault("driver", default_driver)
    encoder = localization.get("encoder")
    if not isinstance(encoder, dict):
        raise JsonDataMigrationError("'localization_sensors.encoder' must be an object")
    configured_sensors = encoder.get("sensors")
    if encoder.get("enabled") is True and (
        not isinstance(configured_sensors, list) or not configured_sensors
    ):
        raise JsonDataMigrationError(
            "Enabled legacy external encoder configuration cannot be mapped to "
            "left/right hardware; disable it and configure explicit sensors"
        )
    encoder.pop("driver", None)
    encoder.setdefault("sensors", [])
    localization.setdefault(
        "steering",
        {
            "enabled": False,
            "driver": "as5048a",
        },
    )
    return data


__all__ = ["migrate_to_v6"]
