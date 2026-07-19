from app.migrations.json_data import JsonDataMigrationError, JsonObject

PROFILE_FIELDS = {
    "confidence",
    "img_size",
    "labels",
    "available_labels",
    "overlay_draw_threshold",
    "overlay_style",
    "segmentation_detail",
    "keypoint_confidence_threshold",
}


def migrate_to_v1(data: JsonObject) -> JsonObject:
    """Move a legacy flat detection configuration into a model profile."""
    profiles = data.get("profiles")
    if profiles is not None and not isinstance(profiles, dict):
        raise JsonDataMigrationError("'profiles' must be an object")

    selected_model = data.get("selected_model", data.get("model"))
    if selected_model is not None and not isinstance(selected_model, str):
        raise JsonDataMigrationError("'selected_model' must be a string or null")

    next_profiles = dict(profiles or {})
    if selected_model and selected_model not in next_profiles:
        legacy_profile = {key: data[key] for key in PROFILE_FIELDS if key in data}
        if legacy_profile:
            next_profiles[selected_model] = legacy_profile

    for field in PROFILE_FIELDS | {"model", "active"}:
        data.pop(field, None)

    data["selected_model"] = selected_model
    data["profiles"] = next_profiles
    return data
