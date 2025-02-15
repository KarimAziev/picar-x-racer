"""
This module handles file operations such as listing, saving, and removing photos, music, and sound files.
It also manages user settings and loads audio details using the `AudioService`.
"""

import json
import os
from os import path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from app.config.config import settings as app_config
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.file_exceptions import DefaultFileRemoveAttempt, InvalidFileName
from app.managers.json_data_manager import JsonDataManager
from app.services.video_service import FileDetails
from app.util.atomic_write import atomic_write
from app.util.file_util import (
    get_directory_structure,
    load_json_file,
    resolve_absolute_path,
)
from app.util.google_coral import is_google_coral_connected
from fastapi import UploadFile
from ultralytics.utils.downloads import GITHUB_ASSETS_STEMS

if TYPE_CHECKING:
    from app.services.audio_service import AudioService
    from app.services.video_service import VideoService

logger = Logger(name=__name__)


class FileService(metaclass=SingletonMeta):
    """
    Service for managing file operations related to user settings, photos, and music.
    """

    def __init__(
        self,
        audio_service: "AudioService",
        video_service: "VideoService",
        user_music_dir=app_config.PX_MUSIC_DIR,
        user_photos_dir=app_config.PX_PHOTO_DIR,
        user_settings_file=app_config.PX_SETTINGS_FILE,
        music_cache_path=app_config.MUSIC_CACHE_FILE_PATH,
        default_user_settings_file=app_config.DEFAULT_USER_SETTINGS,
        default_user_music_dir=app_config.DEFAULT_MUSIC_DIR,
        config_file=app_config.ROBOT_CONFIG_FILE,
        data_dir=app_config.DATA_DIR,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.video_service = video_service

        self.default_user_settings_file = default_user_settings_file
        self.default_user_music_dir = default_user_music_dir
        self.user_settings_file = user_settings_file
        self.user_photos_dir = user_photos_dir
        self.user_music_dir = user_music_dir
        self.config_file = config_file
        self.audio_service = audio_service

        self.music_cache_path = music_cache_path
        self.data_dir = data_dir

        self.cache: Optional[Dict[str, Any]] = None
        self.settings_manager = JsonDataManager(
            target_file=self.user_settings_file,
            template_file=self.default_user_settings_file,
        )
        self.settings_manager.on(
            self.settings_manager.UPDATE_EVENT, self._reload_settings
        )

        self.settings_manager.on(
            self.settings_manager.LOAD_EVENT, self._reload_settings
        )
        self.settings: Dict[str, Any] = self.settings_manager.load_data()

    def _reload_settings(self, data: Dict[str, Any]):
        self.settings = data

    def load_music_cache(self) -> Dict[str, Any]:
        """Load cached audio file data from a persistent file."""
        if os.path.exists(self.music_cache_path):
            return load_json_file(self.music_cache_path)
        else:
            return {}

    def save_music_cache(self) -> None:
        """Save the music cache to a persistent file."""
        with atomic_write(self.music_cache_path) as tmp:
            json.dump(self.cache, tmp, indent=2)

    def load_settings(self) -> Dict[str, Any]:
        """Loads user settings from a JSON file, using cache if file is not modified."""
        return self.settings_manager.load_data()

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves new settings to the user settings file.
        """
        return self.settings_manager.merge(new_settings)

    def list_files(self, directory: str, full=False) -> List[str]:
        """
        Lists all files in the specified directory.

        Args:
            directory (str): The directory to list files from.
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of files in the directory.
        """
        if not os.path.exists(directory):
            return []

        files = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                files.append(file if not full else file_path)
        return files

    def list_files_sorted(self, directory: str, full=False) -> List[str]:
        """
        Lists all files in the specified directory, sorted by modified time.

        Args:
            directory (str): The directory to list files from.
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of files in the directory.
        """
        if not os.path.exists(directory):
            return []

        files = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                files.append(
                    (file if not full else file_path, os.path.getmtime(file_path))
                )

        files.sort(key=lambda x: x[1], reverse=True)

        return [file[0] for file in files]

    def list_all_music_with_details(self) -> List[Dict[str, Any]]:
        """List all music files with cached details, applying the user-defined order if available."""
        defaults = self.list_default_music(full=True)
        user_music = self.list_user_music(full=True)
        all_files = defaults + user_music

        result = []
        for file in all_files:
            details = self.get_audio_file_details(file)
            if details:
                details["removable"] = file in user_music
                result.append(details)

        custom_order = self.get_custom_music_order()
        if custom_order:
            result.sort(
                key=lambda x: (
                    custom_order.index(x["track"])
                    if x["track"] in custom_order
                    else len(custom_order)
                )
            )

        return result

    def list_music_tracks_sorted(self) -> List[str]:
        """List sorted music tracks."""
        return [details["track"] for details in self.list_all_music_with_details()]

    def _get_audio_file_details(self, file: str) -> Optional[Dict[str, Any]]:
        """
        Gets details of an audio file such as track name and duration.

        Args:
            file (str): File path of the audio file.

        Returns:
            dict: A dictionary with track name and duration.
        """
        try:
            duration = self.audio_service.get_audio_duration(file)
            track: str = path.basename(file)
            result = {"track": track, "duration": duration}
            return result
        except Exception:
            logger.error(f"Error getting details for file {file}", exc_info=True)

    def get_audio_file_details(self, file: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves audio file details from cache if available and fresh.
        Otherwise, it will calculate and store the details in cache.
        """
        file_mod_time = os.path.getmtime(file)
        if self.cache is None:
            self.cache = self.load_music_cache()

        if file in self.cache:
            cached_data = self.cache[file]
            cached_mod_time = cached_data["modified_time"]

            if cached_mod_time == file_mod_time:
                logger.debug(
                    "Using cached details for %s",
                    file,
                )
                return cached_data["details"]

        logger.debug(
            "Refreshing details for %s",
            file,
        )
        details = self._get_audio_file_details(file)
        if details:
            self.cache[file] = {
                "modified_time": file_mod_time,
                "details": details,
            }
            self.save_music_cache()
        return details

    def music_track_to_absolute(self, track: str) -> str:
        dir = self.get_music_directory(track)
        return path.join(dir, track)

    def get_custom_music_order(self) -> List[str]:
        """
        Retrieves the custom music track order from the user settings.

        Returns:
            List[str]: List of filenames in the specified custom order.
        """
        settings = self.load_settings()

        return settings.get("music", {"order": []}).get("order", [])

    def save_custom_music_order(self, order: List[str]) -> None:
        """
        Saves the custom music track order to the user settings.

        Args:
            order (List[str]): The custom track order to save.
        """
        existing_settings = self.load_settings()
        music_settings = existing_settings.get("music", {})
        merged_music_settings = {**music_settings, **{"order": order}}

        self.save_settings({"music": merged_music_settings})

    def list_default_music(self, full=False) -> List[str]:
        """
        Lists default music files.

        Args:
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of default music files.
        """

        return self.list_files(self.default_user_music_dir, full)

    def list_user_photos(self, full=False) -> List[str]:
        """
        Lists captured by user photo files.

        Args:
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of user-uploaded photo files.
        """
        return self.list_files_sorted(self.user_photos_dir, full)

    def list_user_videos(self, full=False) -> List[str]:
        """
        Lists captured by user video files.

        Args:
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of user-uploaded video files.
        """
        return self.list_files_sorted(self.video_service.video_dir, full)

    def list_user_videos_detailed(self) -> List[FileDetails]:
        """Recursively lists all video files in the video directory and returns their details."""
        return self.video_service.list_videos_with_details()

    def preview_video_image(self, image_filename: str) -> str:
        """Return full filename for image filename, relative to video preview cache directory."""
        return self.video_service.expand_preview_image(image_filename)

    def list_user_photos_with_preview(self) -> List[dict[str, str]]:
        """
        Lists captured by user photo files.
        """
        files = []
        directory = self.user_photos_dir
        if not path.exists(directory):
            return files

        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            file_item = {
                "name": file,
                "path": file_path,
                "url": file,
            }
            files.append(file_item)

        files.sort(key=lambda x: os.path.getmtime(x["path"]), reverse=True)

        return files

    def list_user_music(self, full=False) -> List[str]:
        """
        Lists user-uploaded music files.

        Args:
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of user-uploaded music files.
        """
        return self.list_files(self.user_music_dir, full)

    @staticmethod
    def remove_file_safe(file_path: str) -> None:
        """Deletes a given file from disk."""
        logger.info("Removing '%s'", file_path)
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
        except Exception:
            logger.error(
                f"Unexpected error while removing '{file_path}'", exc_info=True
            )

    def remove_file(self, file: str, directory: str):
        """
        Removes a file from a specified directory.

        Args:
            file (str): Name of the file to be removed.
            directory (str): Directory from which the file should be removed.

        Returns:
            bool: True if the file was successfully removed.
        """
        logger.info(f"Request to remove {file} in directory {directory}")
        full_name = os.path.join(directory, file)

        os.remove(full_name)
        return True

    def save_music(self, file: UploadFile) -> str:
        """
        Saves the uploaded file to the user's music directory.
        """
        return self.save_uploaded_file(file, self.user_music_dir)

    def save_photo(self, file: UploadFile) -> str:
        """
        Saves the uploaded file to the user's photos directory.
        """
        return self.save_uploaded_file(file, self.user_photos_dir)

    def save_data(self, file: UploadFile) -> str:
        """
        Saves the uploaded file to the data directory.
        """
        return self.save_uploaded_file(file, app_config.DATA_DIR)

    def save_video(self, file: UploadFile) -> str:
        """
        Saves the uploaded file to the data directory.
        """
        return self.save_uploaded_file(file, app_config.PX_VIDEO_DIR)

    def remove_photo(self, filename: str) -> bool:
        """
        Removes a photo file from the user's photo directory.

        Args:
            filename (str): Name of the photo file to be removed.

        Returns:
            bool: True if the file was successfully removed.
        """

        return self.remove_file(filename, self.user_photos_dir)

    def remove_video(self, filename: str) -> bool:
        """
        Removes a video file from the user's video directory.

        Args:
            filename (str): Name of the video file to be removed.

        Returns:
            bool: True if the file was successfully removed.
        """

        self.video_service.remove_video(filename)
        return True

    def remove_music(self, filename: str) -> bool:
        """
        Removes a music file from the user's music directory or prevents default music files from being removed.

        Args:
            filename (str): Name of the music file to be removed.

        Raises:
            DefaultFileRemoveAttempt: If attempting to remove a default music file.
            FileNotFoundError: If the file doesn't exist.

        Returns:
            bool: True if the file was successfully removed.
        """

        logger.info(f"Removing music file {filename}")
        if path.exists(path.join(self.user_music_dir, filename)):
            self.remove_file(filename, self.user_music_dir)

            custom_order = self.get_custom_music_order()
            if filename in custom_order:
                custom_order.remove(filename)
                self.save_custom_music_order(custom_order)

            return True
        elif path.exists(path.join(self.default_user_music_dir, filename)):
            raise DefaultFileRemoveAttempt("Cannot remove the default file.")
        else:
            logger.error("The file '%s' was not found", filename)
            raise FileNotFoundError("File not found")

    def remove_data(self, filename: str) -> bool:
        """
        Removes a file from the data directory.

        Args:
            filename (str): Name of the file to be removed.

        Returns:
            bool: True if the file was successfully removed.
        """

        os.remove(resolve_absolute_path(filename, app_config.DATA_DIR))
        return True

    def get_photo_directory(self, filename: str) -> str:
        """
        Retrieves the directory of a specified photo file.

        Args:
            filename (str): Name of the photo file.

        Raises:
            FileNotFoundError: If the file doesn't exist.

        Returns:
            str: Directory path of the photo file.
        """

        user_file = path.join(self.user_photos_dir, filename)
        if path.exists(user_file):
            return self.user_photos_dir
        else:
            logger.error("The file '%s' was not found", user_file)
            raise FileNotFoundError("File not found")

    def get_video_directory(self, filename: str) -> str:
        """
        Retrieves the directory of a specified video file.

        Args:
            filename (str): Name of the video file.

        Raises:
            FileNotFoundError: If the file doesn't exist.

        Returns:
            str: Directory path of the video file.
        """

        user_file = path.join(self.video_service.video_dir, filename)
        if path.exists(user_file):
            return self.video_service.video_dir
        else:
            logger.error("The file '%s' was not found", user_file)
            raise FileNotFoundError("File not found")

    def get_music_directory(self, filename: str) -> str:
        """
        Retrieves the directory of a specified music file.

        Args:
            filename (str): Name of the music file.

        Raises:
            FileNotFoundError: If the file doesn't exist.

        Returns:
            str: Directory path of the music file.
        """

        user_file = path.join(self.user_music_dir, filename)
        if path.exists(user_file):
            return self.user_music_dir
        elif path.exists(path.join(self.default_user_music_dir, filename)):
            return self.default_user_music_dir
        else:
            logger.error("The file '%s' was not found", user_file)
            raise FileNotFoundError("File not found")

    def save_uploaded_file(self, file: UploadFile, directory: str) -> str:
        """
        Saves an uploaded file to the specified directory.

        Args:
            file (UploadFile): The uploaded file.
            directory (str): The directory where the file should be saved.

        Raises:
            ValueError: If the filename is invalid.

        Returns:
            str: The path of the saved file.
        """
        filename = file.filename
        if not filename:
            raise InvalidFileName("Invalid filename.")

        file_path = os.path.join(directory, filename)

        with atomic_write(file_path, mode="wb") as buffer:
            buffer.write(file.file.read())
        return file_path

    def get_calibration_config(self) -> Dict[str, Any]:
        """
        Loads calibration settings from a configuration file.

        Returns:
            dict: Calibration settings in JSON format.
        """

        config = self.get_robot_config()

        return {
            "steering_servo_offset": config.get("steering_servo", {}).get(
                "calibration_offset"
            ),
            "cam_tilt_servo_offset": config.get("cam_tilt_servo", {}).get(
                "calibration_offset"
            ),
            "cam_pan_servo_offset": config.get("cam_pan_servo", {}).get(
                "calibration_offset"
            ),
            "left_motor_direction": config.get("left_motor", {}).get(
                "calibration_direction"
            ),
            "right_motor_direction": config.get("right_motor", {}).get(
                "calibration_direction"
            ),
        }

    def get_robot_config(self) -> Dict[str, Any]:
        """
        Loads calibration settings from a configuration file.

        Returns:
            dict: Calibration settings in JSON format.
        """

        if path.exists(self.config_file):
            return load_json_file(self.config_file)
        return load_json_file(app_config.DEFAULT_ROBOT_CONFIG_FILE)

    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        """
        Recursively scans the provided directory for .tflite, .onnx and .pt model files.
        Returns a structed list of all found models.
        """

        allowed_extensions: Tuple[str, ...] = tuple(
            [
                ext
                for ext in [
                    ".tflite" if is_google_coral_connected() else None,
                    ".pt",
                    ".hef",
                    ".onnx",
                ]
                if ext
            ]
        )

        existing_set: Set[str] = set()

        result = get_directory_structure(
            app_config.DATA_DIR,
            allowed_extensions,
            directory_suffix="_ncnn_model",
            exclude_empty_dirs=True,
            absolute=False,
            file_processor=lambda file_path: existing_set.add(
                os.path.basename(file_path)
            ),
        )

        for key in GITHUB_ASSETS_STEMS:
            if not key in existing_set and not key.endswith(
                ("-cls", "-seg", ".npy", "-obb")
            ):
                item = {
                    "label": key,
                    "key": key,
                    "selectable": True,
                    "data": {"name": key, "type": "Loadable model"},
                }
                result.append(item)

        return result
