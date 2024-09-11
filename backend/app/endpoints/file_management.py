from typing import TYPE_CHECKING

from app.exceptions.file_controller import DefaultFileRemoveAttempt
from app.util.logger import Logger
from flask import Blueprint, current_app, jsonify, request, send_from_directory

if TYPE_CHECKING:
    from app.controllers.files_controller import FilesController

file_management_bp = Blueprint("file_management", __name__)
logger = Logger(__name__)


@file_management_bp.route("/api/list_files/<media_type>", methods=["GET"])
def list_files(media_type):
    file_manager: "FilesController" = current_app.config["file_manager"]

    if media_type == "music":
        files = file_manager.list_user_music()
        logger.debug(f"music files {files}")
    elif media_type == "default_music":
        files = file_manager.list_default_music()
    elif media_type == "default_sound":
        files = file_manager.list_default_sounds()
    elif media_type == "sound":
        files = file_manager.list_user_sounds()
    elif media_type == "image":
        files = file_manager.list_user_photos()
    else:
        return jsonify({"error": "Invalid media type"}), 400

    return jsonify({"files": files})


@file_management_bp.route("/api/upload/<media_type>", methods=["POST"])
def upload_file(media_type):
    file_manager: "FilesController" = current_app.config["file_manager"]

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if media_type == "music":
        file_manager.save_music(file)
    elif media_type == "sound":
        file_manager.save_sound(file)
    elif media_type == "image":
        file_manager.save_photo(file)
    else:
        return jsonify({"error": "Invalid media type"}), 400

    return jsonify({"success": True, "filename": file.filename})


@file_management_bp.route("/api/remove_file/<media_type>", methods=["DELETE"])
def remove_file(media_type):
    file_manager: "FilesController" = current_app.config["file_manager"]

    data = request.get_json()
    if not data or "filename" not in data:
        return jsonify({"error": "No filename provided"}), 400

    filename = data["filename"]

    try:
        if media_type == "music":
            file_manager.remove_music(filename)
            return jsonify({"success": True, "filename": filename})
        elif media_type == "sound":
            file_manager.remove_sound(filename)
            return jsonify({"success": True, "filename": filename})
        elif media_type == "image":
            file_manager.remove_photo(filename)
            return jsonify({"success": True, "filename": filename})
        else:
            return jsonify({"error": "Invalid media type"}), 400

    except DefaultFileRemoveAttempt as e:
        logger.warning(f"Duplicate notification attempted: {e}")
        return jsonify({"error": str(e)}), 400
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@file_management_bp.route("/api/download/<media_type>/<filename>", methods=["GET"])
def download_file(media_type, filename):
    file_manager: "FilesController" = current_app.config["file_manager"]

    try:
        if media_type == "music":
            directory = file_manager.get_music_directory(filename)
            return send_from_directory(directory, filename, as_attachment=True)
        elif media_type == "sound":
            directory = file_manager.get_sound_directory(filename)
            return send_from_directory(directory, filename, as_attachment=True)
        elif media_type == "image":
            directory = file_manager.get_photo_directory(filename)
            return send_from_directory(directory, filename, as_attachment=True)
        else:
            return jsonify({"error": "Invalid media type"}), 400

    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
