from app.migrations.json_data import JsonDataMigrationError, JsonObject

NMS_DEFAULTS = {
    "iou_threshold": 0.7,
    "max_detections": 5,
}


def migrate_to_v2(data: JsonObject) -> JsonObject:
    """Add per-model non-maximum suppression settings."""
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        raise JsonDataMigrationError("'profiles' must be an object")

    selected_model = data.get("selected_model")
    for model, profile in profiles.items():
        if not isinstance(profile, dict):
            raise JsonDataMigrationError(f"Profile '{model}' must be an object")
        for field, default in NMS_DEFAULTS.items():
            profile.setdefault(field, default)

    if isinstance(selected_model, str) and selected_model in profiles:
        selected_profile = profiles[selected_model]
        for field in NMS_DEFAULTS:
            if field in data:
                selected_profile[field] = data[field]

    for field in NMS_DEFAULTS:
        data.pop(field, None)

    return data
