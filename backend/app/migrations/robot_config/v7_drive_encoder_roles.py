from app.migrations.json_data import JsonDataMigrationError, JsonObject


_SIDE_TO_ROLE = {
    "left": "left_wheel",
    "right": "right_wheel",
}
_ROLES = {*_SIDE_TO_ROLE.values(), "rear_axle_average"}


def migrate_to_v7(data: JsonObject) -> JsonObject:
    """Replace physical encoder sides with explicit kinematic roles."""

    localization = data.get("localization_sensors")
    if not isinstance(localization, dict):
        raise JsonDataMigrationError("'localization_sensors' must be an object")
    encoder = localization.get("encoder")
    if not isinstance(encoder, dict):
        raise JsonDataMigrationError("'localization_sensors.encoder' must be an object")
    sensors = encoder.get("sensors")
    if not isinstance(sensors, list):
        raise JsonDataMigrationError(
            "'localization_sensors.encoder.sensors' must be an array"
        )

    for index, sensor in enumerate(sensors):
        path = f"localization_sensors.encoder.sensors[{index}]"
        if not isinstance(sensor, dict):
            raise JsonDataMigrationError(f"'{path}' must be an object")
        has_side = "side" in sensor
        has_role = "role" in sensor
        if has_side and has_role:
            raise JsonDataMigrationError(
                f"'{path}' cannot contain both legacy 'side' and new 'role'"
            )
        if has_side:
            side = sensor.pop("side")
            role = _SIDE_TO_ROLE.get(side) if isinstance(side, str) else None
            if role is None:
                raise JsonDataMigrationError(f"'{path}.side' must be 'left' or 'right'")
            sensor["role"] = role
        else:
            role = sensor.get("role")
            if isinstance(role, str) and role in _ROLES:
                continue
            raise JsonDataMigrationError(
                f"'{path}' requires a valid legacy 'side' or new 'role'"
            )

    return data


__all__ = ["migrate_to_v7"]
