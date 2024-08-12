from typing import TYPE_CHECKING
from flask import Blueprint, current_app, jsonify, request

if TYPE_CHECKING:
    from controllers.video_car_controller import VideoCarController

file_management_bp = Blueprint("file_management", __name__)


@file_management_bp.route("/api/list_files/<media_type>", methods=["GET"])
def list_files(media_type):
    vc: "VideoCarController" = current_app.config["vc"]

    if media_type == "music":
        directory = vc.MUSIC_DIR
    elif media_type == "sounds":
        directory = vc.SOUNDS_DIR
    else:
        return jsonify({"error": "Invalid media type"}), 400

    files = vc.list_files(directory)
    return jsonify({"files": files})


@file_management_bp.route("/api/upload/<media_type>", methods=["POST"])
def upload_file(media_type):
    vc: "VideoCarController" = current_app.config["vc"]

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if media_type == "music":
        directory = vc.MUSIC_DIR
    elif media_type == "sounds":
        directory = vc.SOUNDS_DIR
    else:
        return jsonify({"error": "Invalid media type"}), 400

    vc.save_file(file, directory)
    return jsonify({"success": True, "filename": file.filename})
