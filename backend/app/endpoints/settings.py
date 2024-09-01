from flask import Blueprint, jsonify, request, current_app
from typing import TYPE_CHECKING, Dict, Any, Union


if TYPE_CHECKING:
    from app.controllers.files_controller import FilesController


settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/api/settings", methods=["GET"])
def get_settings():
    vc: "FilesController" = current_app.config["file_manager"]
    return jsonify(vc.load_settings())


@settings_bp.route("/api/settings", methods=["POST"])
def update_settings():
    vc: "FilesController" = current_app.config["file_manager"]
    new_settings: Union[Dict[str, Any], None] = request.json

    if not isinstance(new_settings, dict):
        return jsonify({"error": "Invalid settings format"}), 400

    vc.save_settings(new_settings)
    return jsonify({"success": True, "settings": new_settings})


@settings_bp.route("/api/calibration", methods=["GET"])
def get_calibration_settings():
    vc: "FilesController" = current_app.config["file_manager"]
    return jsonify(vc.get_calibration_config())
