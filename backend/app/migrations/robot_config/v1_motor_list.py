from app.migrations.json_data import JsonDataMigrationError, JsonObject

LEGACY_MOTOR_FIELDS = ("left_motor", "right_motor")
REMOVED_MOTOR_FIELDS = ("calibration_speed_offset", "period", "prescaler")


def migrate_to_v1(data: JsonObject) -> JsonObject:
    """Replace fixed left/right motors with the bounded motors collection."""
    legacy_motors = [data.get(field) for field in LEGACY_MOTOR_FIELDS]
    has_legacy_motors = any(motor is not None for motor in legacy_motors)

    if "motors" in data and has_legacy_motors:
        raise JsonDataMigrationError(
            "Hardware config contains both legacy motor fields and 'motors'"
        )

    if "motors" not in data:
        data["motors"] = [motor for motor in legacy_motors if isinstance(motor, dict)]

    for field in LEGACY_MOTOR_FIELDS:
        data.pop(field, None)

    motors = data.get("motors")
    if not isinstance(motors, list):
        raise JsonDataMigrationError("'motors' must be an array")

    for motor in motors:
        if not isinstance(motor, dict):
            raise JsonDataMigrationError("Each motor configuration must be an object")
        if "pwm_pin" in motor and "channel" not in motor:
            motor["channel"] = motor.pop("pwm_pin")
        for field in REMOVED_MOTOR_FIELDS:
            motor.pop(field, None)

    return data
