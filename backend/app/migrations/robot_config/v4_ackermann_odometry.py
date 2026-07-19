from app.migrations.json_data import JsonDataMigrationError, JsonObject


def migrate_to_v4(data: JsonObject) -> JsonObject:
    """Add disabled odometry without guessing vehicle geometry."""

    odometry = data.get("ackermann_odometry")
    if odometry is None:
        data["ackermann_odometry"] = {"enabled": False}
    elif not isinstance(odometry, dict):
        raise JsonDataMigrationError("'ackermann_odometry' must be an object or null")
    return data
