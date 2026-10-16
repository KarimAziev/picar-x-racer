from app.migrations.json_data import JsonDataMigrationError, JsonObject


def migrate_to_v8(data: JsonObject) -> JsonObject:
    """Persist the nominal pulse-angle calibration independently of travel limits."""
    for name in ("steering_servo", "cam_pan_servo", "cam_tilt_servo"):
        servo = data.get(name)
        if not isinstance(servo, dict):
            raise JsonDataMigrationError(f"'{name}' must be an object")
        has_min = "real_min_angle" in servo
        has_max = "real_max_angle" in servo
        if has_min != has_max:
            raise JsonDataMigrationError(
                f"'{name}' must specify both real_min_angle and real_max_angle"
            )
        if not has_min:
            # Travel limits do not contain measurements of pulse-to-angle response.
            servo["real_min_angle"] = -90.0
            servo["real_max_angle"] = 90.0
    return data


__all__ = ["migrate_to_v8"]
