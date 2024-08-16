from typing import TYPE_CHECKING
from flask import Blueprint, current_app, jsonify, request, send_from_directory

if TYPE_CHECKING:
    from controllers.video_car_controller import VideoCarController

file_management_bp = Blueprint("file_management", __name__)


@file_management_bp.route("/api/list_files/<media_type>", methods=["GET"])
def list_files(media_type):
    vc: "VideoCarController" = current_app.config["vc"]

    if media_type == "music":
        directory = vc.MUSIC_DIR
    elif media_type == "sound":
        directory = vc.SOUNDS_DIR
    elif media_type == "image":
        directory = vc.PHOTOS_DIR
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
    elif media_type == "sound":
        directory = vc.SOUNDS_DIR
    elif media_type == "image":
        directory = vc.PHOTOS_DIR
    else:
        return jsonify({"error": "Invalid media type"}), 400

    vc.save_file(file, directory)
    return jsonify({"success": True, "filename": file.filename})


@file_management_bp.route("/api/remove_file/<media_type>", methods=["DELETE"])
def remove_file(media_type):
    vc: "VideoCarController" = current_app.config["vc"]

    data = request.get_json()
    if not data or "filename" not in data:
        return jsonify({"error": "No filename provided"}), 400

    filename = data["filename"]

    if media_type == "music":
        directory = vc.MUSIC_DIR
    elif media_type == "sound":
        directory = vc.SOUNDS_DIR
    elif media_type == "image":
        directory = vc.PHOTOS_DIR
    else:
        return jsonify({"error": "Invalid media type"}), 400

    success = vc.remove_file(filename, directory)
    if success:
        return jsonify({"success": True, "filename": filename})
    else:
        return jsonify({"error": "File not found"}), 404


@file_management_bp.route("/api/download/<media_type>/<filename>", methods=["GET"])
def download_file(media_type, filename):
    vc: "VideoCarController" = current_app.config["vc"]

    if media_type == "music":
        directory = vc.MUSIC_DIR
    elif media_type == "sound":
        directory = vc.SOUNDS_DIR
    elif media_type == "image":
        directory = vc.PHOTOS_DIR
    else:
        return jsonify({"error": "Invalid media type"}), 400

    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
