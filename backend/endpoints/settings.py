from flask import Blueprint, jsonify, request, current_app
from typing import TYPE_CHECKING, Dict, Any, Union

if TYPE_CHECKING:
    from controllers.video_car_controller import VideoCarController


settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/api/settings", methods=["GET"])
def get_settings():
    vc: "VideoCarController" = current_app.config["vc"]
    return jsonify(vc.settings)


@settings_bp.route("/api/settings", methods=["POST"])
def update_settings():
    vc: "VideoCarController" = current_app.config["vc"]
    new_settings: Union[Dict[str, Any], None] = request.json

    if not isinstance(new_settings, dict):
        return jsonify({"error": "Invalid settings format"}), 400

    vc.save_settings(new_settings)
    return jsonify({"success": True, "settings": new_settings})
