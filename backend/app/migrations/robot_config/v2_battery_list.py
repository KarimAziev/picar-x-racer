from typing import Any

from app.migrations.json_data import JsonDataMigrationError, JsonObject


def migrate_to_v2(data: JsonObject) -> JsonObject:
    """Replace the singular battery configuration with a named collection."""
    legacy_battery = data.get("battery")
    if "batteries" in data and legacy_battery is not None:
        raise JsonDataMigrationError(
            "Hardware config contains both legacy 'battery' and 'batteries'"
        )

    if legacy_battery is not None and not isinstance(legacy_battery, dict):
        raise JsonDataMigrationError("Legacy 'battery' must be an object or null")

    if "batteries" not in data:
        batteries: list[dict[str, Any]] = []
        if legacy_battery is not None:
            legacy_battery.setdefault("name", "Main battery")
            batteries.append(legacy_battery)
        data["batteries"] = batteries

    data.pop("battery", None)
    return data
