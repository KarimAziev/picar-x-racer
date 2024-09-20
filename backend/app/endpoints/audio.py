from os import path
from typing import TYPE_CHECKING, Any, Dict, Union

from app.util.logger import Logger
from quart import Blueprint, current_app, jsonify, request

if TYPE_CHECKING:
    from app.controllers.audio_controller import AudioController
    from app.controllers.files_controller import FilesController

audio_management_bp = Blueprint("audio_management", __name__)
logger = Logger(__name__)


@audio_management_bp.route("/api/play-sound", methods=["POST"])
async def play_sound():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    payload: Union[Dict[str, Any], None] = await request.json

    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid settings format"}), 400
    filename = payload["filename"]
    force = payload.get("force", False)

    logger.info(f"Request to play sound {filename}")
    try:
        dir = file_manager.get_sound_directory(filename)
        file = path.join(dir, filename)
        result = audio_manager.play_sound(file, force)
        return jsonify(result)
    except FileNotFoundError as err:
        return jsonify({"error": str(err)}), 404
    except Exception as err:
        return jsonify({"error": str(err)}), 500


@audio_management_bp.route("/api/play-status", methods=["GET"])
async def get_play_status():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    result = audio_manager.get_music_play_status()

    if result is None:
        default_track = file_manager.load_settings()
        track = default_track.get("default_music")
        dir = file_manager.get_music_directory(track)
        file = path.join(dir, track)
        duration = audio_manager.music.music_get_duration(file)
        return jsonify({"playing": False, "track": track, "duration": duration})
    else:
        return jsonify(result)


@audio_management_bp.route("/api/play-music", methods=["POST"])
async def play_music():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    payload: Union[Dict[str, Any], None] = await request.json

    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid settings format"}), 400
    filename = payload["filename"]
    force = payload.get("force", False)
    start = payload.get("start", 0.0)
    logger.info(f"request to play music {filename}")
    if filename is None:
        result = audio_manager.stop_music()
        return jsonify({"playing": audio_manager.is_music_playing()})
    try:
        dir = file_manager.get_music_directory(filename)
        file = path.join(dir, filename)
        logger.debug(f"playing {file}")
        result = audio_manager.play_music(track_path=file, force=force, start=start)
        return jsonify(result)
    except Exception as err:
        return jsonify({"error": str(err)}), 500


@audio_management_bp.route("/api/play-tts", methods=["POST"])
async def text_to_speech():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    payload: Union[Dict[str, str], None] = await request.json

    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid settings format"}), 400
    if not audio_manager.google_speech_available:
        return jsonify({"error": "Google speech is not available"}), 404

    if not payload.get("text"):
        settings = file_manager.load_settings()
        text = settings.get("default_text")
        lang = settings.get("default_language", "en")
    else:
        text = payload.get("text")
        lang = payload.get("lang", "en")

    if text and lang:
        audio_manager.text_to_speech(text, lang)
        return jsonify({"status": True})
    else:
        return jsonify({"error": "Invalid settings format"}), 400


@audio_management_bp.route("/api/volume", methods=["POST"])
async def set_volume():
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    payload: Union[Dict[str, int], None] = await request.json
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid format"}), 400
    volume = payload.get("volume")
    if volume is None:
        return jsonify({"error": "Invalid format"}), 400

    logger.info(f"request to set volume to {payload.get('volume')}")
    try:
        logger.debug(f"setting volume to {volume}")
        audio_manager.set_volume(volume)

        return jsonify({"volume": audio_manager.get_volume()})
    except Exception as err:
        return jsonify({"error": str(err)}), 404


@audio_management_bp.route("/api/volume", methods=["GET"])
async def get_volume():
    audio_manager: "AudioController" = current_app.config["audio_manager"]

    try:
        return jsonify({"volume": audio_manager.get_volume()})
    except Exception as err:
        return jsonify({"error": str(err)}), 404


@audio_management_bp.route("/api/music", methods=["GET"])
async def get_music_tracks():
    file_manager: "FilesController" = current_app.config["file_manager"]
    audio_manager: "AudioController" = current_app.config["audio_manager"]
    amixer_volume = audio_manager.get_amixer_volume()
    music_volume = audio_manager.get_volume()
    try:
        files = file_manager.list_all_music_with_details()
        return jsonify(
            {"files": files, "system_volume": amixer_volume, "volume": music_volume}
        )
    except Exception as err:
        return jsonify({"error": str(err)}), 404
