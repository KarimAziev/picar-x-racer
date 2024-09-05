from os import path
from typing import TYPE_CHECKING, Any, Dict, Union

from app.util.logger import Logger
from flask import Blueprint, current_app, jsonify, request

if TYPE_CHECKING:
    from app.controllers.audio_controller import AudioController
    from app.controllers.files_controller import FilesController

audio_management_bp = Blueprint("audio_management", __name__)
logger = Logger(__name__)


@audio_management_bp.route("/api/play-sound", methods=["POST"])
def play_sound():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    payload: Union[Dict[str, Any], None] = request.json

    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid settings format"}), 400
    filename = payload["filename"]

    logger.info(f"request to play {filename}")
    try:
        dir = file_manager.get_sound_directory(filename)
        logger.debug(f"filename {filename} directory {dir}")
        file = path.join(dir, filename)
        logger.debug(f"playing {file}")
        audio_manager.play_sound(file)
        return jsonify(
            {
                "playing": audio_manager.sound_playing,
                "sound_end_time": audio_manager.sound_end_time,
            }
        )
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@audio_management_bp.route("/api/play-music", methods=["POST"])
def play_music():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    payload: Union[Dict[str, Any], None] = request.json

    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid settings format"}), 400
    filename = payload["filename"]

    try:
        dir = file_manager.get_music_directory(filename)
        file = path.join(dir, filename)
        logger.debug(f"playing {file}")
        audio_manager.play_music(file)
        return jsonify({"playing": audio_manager.is_music_playing()})
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@audio_management_bp.route("/api/play-tts", methods=["POST"])
def text_to_speech():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    payload: Union[Dict[str, str], None] = request.json

    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid settings format"}), 400
    if not audio_manager.google_speech_available:
        return jsonify({"error": "Google speech is not available"}), 404

    if not payload.get("text"):
        settings = file_manager.load_settings()
        text = settings["default_text"]
        lang = settings.get("default_language", "en")
    else:
        text = payload.get("text", file_manager.load_settings())
        lang = payload.get("lang", "en")

    if text and lang:
        audio_manager.text_to_speech(text, lang)
        return jsonify({"status": True})
    else:
        return jsonify({"error": "Invalid settings format"}), 400
