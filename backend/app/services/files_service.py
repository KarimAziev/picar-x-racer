"""
FilesService Class

This module handles file operations such as listing, saving, and removing photos, music, and sound files for a user within the application. It also manages user settings and loads audio details using the `AudioService`.

Classes:
    - FilesService: Handles file-related operations including saving, removing, and listing files from specified directories.

Methods:
    - __init__: Initializes the FilesService with user-specific directories and audio manager.
    - get_settings_file: Determines the current settings file to use
    - load_settings: Loads user settings from a cache or JSON file.
    - save_settings: Saves user settings to a JSON file.
    - list_files: Lists all files in a specified directory.
    - list_all_music_with_details: Lists all music files with details (duration).
    - _get_audio_file_details: Retrieves details (track name and duration) of a specific audio file.
    - list_default_music: Lists default music files.
    - list_default_sounds: Lists default sound files.
    - list_user_photos: Lists user-uploaded photo files.
    - list_user_music: Lists user-uploaded music files.
    - list_user_sounds: Lists user-uploaded sound files.
    - remove_file: Removes a file from a specified directory.
    - save_sound: Saves an uploaded sound file to the user’s sound directory.
    - save_music: Saves an uploaded music file to the user’s music directory.
    - save_photo: Saves an uploaded photo file to the user’s photos directory.
    - remove_photo: Removes a photo file from the user’s photo directory.
    - remove_music: Removes a music file from the user’s music directory, preventing default music files from being removed.
    - remove_sound: Removes a sound file from the user’s sound directory, preventing default sound files from being removed.
    - get_photo_directory: Retrieves the directory of a specified photo file.
    - get_sound_directory: Retrieves the directory of a specified sound file.
    - get_music_directory: Retrieves the directory of a specified music file.
    - save_uploaded_file: Saves an uploaded file to a specified directory.
    - get_calibration_config: Loads calibration settings from a configuration file.
"""

import json
import os
from os import path
from typing import Any, Dict, List, Optional

from app.adapters.robot_hat.filedb import fileDB
from app.config.paths import (
    CONFIG_USER_DIR,
    DATA_DIR,
    DEFAULT_MUSIC_DIR,
    DEFAULT_SOUND_DIR,
    DEFAULT_USER_SETTINGS,
    MUSIC_CACHE_FILE_PATH,
    PICARX_CONFIG_FILE,
    PX_MUSIC_DIR,
    PX_PHOTO_DIR,
    PX_SOUND_DIR,
    PX_VIDEO_DIR,
    USER_HOME,
)
from app.exceptions.file_exceptions import DefaultFileRemoveAttempt
from app.services.audio_service import AudioService
from app.util.file_util import (
    ensure_parent_dir_exists,
    file_to_relative,
    get_files_with_extension,
    load_json_file,
    resolve_absolute_path,
)
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from fastapi import UploadFile


class FilesService(metaclass=SingletonMeta):
    """
    Service for managing file operations related to user settings, photos, sounds, and music.

    Args:
        audio_manager (AudioService): An instance of AudioService to handle audio operations.
    """

    default_user_settings_file = DEFAULT_USER_SETTINGS
    default_user_music_dir = DEFAULT_MUSIC_DIR
    default_user_sounds_dir = DEFAULT_SOUND_DIR

    def __init__(self, audio_manager: AudioService, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = Logger(name=__name__)
        self.user_home = USER_HOME
        self.user_settings_file = path.join(
            CONFIG_USER_DIR, "picar-x-racer", "user_settings.json"
        )
        self.user_photos_dir = PX_PHOTO_DIR
        self.user_videos_dir = PX_VIDEO_DIR
        self.user_sounds_dir = PX_SOUND_DIR
        self.user_music_dir = PX_MUSIC_DIR

        self.audio_manager = audio_manager
        self.cache = self.load_cache()

        self.cached_settings = None
        self.last_modified_time = None
        self.current_settings_file = None
        self.settings = self.load_settings()
        self.list_all_music_with_details()

    def load_cache(self):
        """Load cached audio file data from a persistent file."""
        if os.path.exists(MUSIC_CACHE_FILE_PATH):
            with open(MUSIC_CACHE_FILE_PATH, "r") as cache_file:
                return json.load(cache_file)
        return {}

    def save_cache(self):
        """Save the cache to a persistent file."""
        ensure_parent_dir_exists(MUSIC_CACHE_FILE_PATH)
        with open(MUSIC_CACHE_FILE_PATH, "w") as cache_file:
            json.dump(self.cache, cache_file, indent=2)

    def get_settings_file(self):
        """Determines the current settings file to use"""
        return (
            self.user_settings_file
            if os.path.exists(self.user_settings_file)
            else FilesService.default_user_settings_file
        )

    def load_settings(self):
        """Loads user settings from a JSON file, using cache if file is not modified."""
        settings_file = self.get_settings_file()

        try:
            current_modified_time = os.path.getmtime(settings_file)
        except OSError:
            current_modified_time = None

        if (
            self.cached_settings is None
            or self.last_modified_time != current_modified_time
            or self.current_settings_file != settings_file
        ):
            self.logger.info(f"Loading settings from {settings_file}")
            self.cached_settings = load_json_file(settings_file)
            self.last_modified_time = current_modified_time
            self.current_settings_file = settings_file
        else:
            self.logger.debug(
                f"Using cached settings from {self.current_settings_file}"
            )

        return self.cached_settings

    def save_settings(self, new_settings: Dict[str, Any]):
        """Saves new settings to the user settings file."""
        existing_settings = self.load_settings()
        self.logger.info(f"Saving settings to {self.user_settings_file}")

        merged_settings = {
            **existing_settings,
            **new_settings,
        }
        self.logger.debug(f"New settings {new_settings}")
        self.logger.debug(f"Merged settings {merged_settings}")
        ensure_parent_dir_exists(self.user_settings_file)

        with open(self.user_settings_file, "w") as settings_file:
            json.dump(merged_settings, settings_file, indent=2)

        self.settings = merged_settings
        self.logger.debug(f"Settings saved to {self.user_settings_file}")
        return self.settings

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

    def prune_cache(self, max_entries=100):
        """Limits the cache size by keeping only recent entries."""
        if len(self.cache) > max_entries:
            # Keeps the N most popular/most recent entries
            self.cache = dict(list(self.cache.items())[-max_entries:])
            self.save_cache()

    def update_track_order_in_cache(self, ordered_tracks: List[str]):
        """
        Updates the order for tracks in the music cache.

        Args:
            ordered_tracks (List[str]): List of track filenames in the desired order.
        """
        for idx, track_filename in enumerate(ordered_tracks):
            for _, cache_entry in self.cache.items():
                if cache_entry["details"]["track"] == track_filename:
                    self.logger.debug(f"Updating order for track: {track_filename}")
                    cache_entry["details"]["order"] = idx
                    break
        self.save_cache()

    def _get_audio_file_details(self, file: str):
        """
        Gets details of an audio file such as track name and duration.

        Args:
            file (str): File path of the audio file.

        Returns:
            dict: A dictionary with track name and duration.
        """
        try:
            duration = self.audio_manager.music.music_get_duration(file)
            track: str = path.basename(file)
            result = {"track": track, "duration": duration}
            return result
        except Exception as err:
            self.logger.log_exception(f"Error getting details for file {file}", err)

    def get_audio_file_details(self, file: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves audio file details from cache if available and fresh.
        Otherwise, it will calculate and store the details in cache.
        """
        file_mod_time = os.path.getmtime(file)

        if file in self.cache:
            cached_data = self.cache[file]
            cached_mod_time = cached_data["modified_time"]

            if cached_mod_time == file_mod_time:
                self.logger.debug(
                    "Using cached details for %s",
                    file,
                )
                return cached_data["details"]

        self.logger.debug(
            "Refreshing details for %s",
            file,
        )
        details = self._get_audio_file_details(file)
        if details:
            self.cache[file] = {
                "modified_time": file_mod_time,
                "details": details,
            }
            self.save_cache()
        return details

    def music_track_to_absolute(self, track: str):
        dir = self.get_music_directory(track)
        return path.join(dir, track)

    def get_custom_music_order(self) -> List[str]:
        """
        Retrieves the custom music track order from the user settings.

        Returns:
            List[str]: List of filenames in the specified custom order.
        """
        settings = self.load_settings()
        return settings.get("music_order", [])

    def save_custom_music_order(self, order: List[str]):
        """
        Saves the custom music track order to the user settings.

        Args:
            order (List[str]): The custom track order to save.
        """
        self.save_settings({"music_order": order})

    def list_default_music(self, full=False):
        """
        Lists default music files.

        Args:
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of default music files.
        """

        return self.list_files(self.default_user_music_dir, full)

    def list_default_sounds(self, full=False):
        """
        Lists default sound files.

        Args:
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of default sound files.
        """

        return self.list_files(self.default_user_sounds_dir, full)

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
        return self.list_files_sorted(self.user_videos_dir, full)

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
            file_item = {"name": file, "path": file_path, "url": f"/api/preview/{file}"}
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

    def list_user_sounds(self, full=False) -> List[str]:
        """
        Lists user-uploaded sound files.

        Args:
            full (bool, optional): Whether to return full file paths. Defaults to False.

        Returns:
            List[str]: List of user-uploaded sound files.
        """

        return self.list_files(self.user_sounds_dir, full)

    def remove_file(self, file: str, directory: str):
        """
        Removes a file from a specified directory.

        Args:
            file (str): Name of the file to be removed.
            directory (str): Directory from which the file should be removed.

        Returns:
            bool: True if the file was successfully removed.
        """
        self.logger.info(f"Request to remove {file} in directory {directory}")
        full_name = os.path.join(directory, file)

        os.remove(full_name)
        return True

    def save_sound(self, file: UploadFile) -> str:
        """
        Saves an uploaded sound file to the user's sound directory.

        Args:
            file (UploadFile): Uploaded sound file.

        Returns:
            str: File path of the saved sound file.
        """
        return self.save_uploaded_file(file, self.user_sounds_dir)

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
        return self.save_uploaded_file(file, DATA_DIR)

    def remove_photo(self, filename: str):
        """
        Removes a photo file from the user's photo directory.

        Args:
            filename (str): Name of the photo file to be removed.

        Returns:
            bool: True if the file was successfully removed.
        """

        return self.remove_file(filename, self.user_photos_dir)

    def remove_video(self, filename: str):
        """
        Removes a video file from the user's video directory.

        Args:
            filename (str): Name of the video file to be removed.

        Returns:
            bool: True if the file was successfully removed.
        """

        return self.remove_file(filename, self.user_videos_dir)

    def remove_music(self, filename: str):
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

        self.logger.info(f"Removing music file {filename}")
        if path.exists(path.join(self.user_music_dir, filename)):
            self.remove_file(filename, self.user_music_dir)

            custom_order = self.get_custom_music_order()
            if filename in custom_order:
                custom_order.remove(filename)
                self.save_custom_music_order(custom_order)

            return True
        elif path.exists(path.join(self.default_user_music_dir, filename)):
            raise DefaultFileRemoveAttempt(
                f"{filename} is default music and cannot be removed!"
            )
        else:
            raise FileNotFoundError

    def remove_sound(self, filename: str) -> bool:
        """
        Removes a sound file from the user's sound directory or prevents default sound files from being removed.

        Args:
            filename (str): Name of the sound file to be removed.

        Raises:
            DefaultFileRemoveAttempt: If attempting to remove a default sound file.
            FileNotFoundError: If the file doesn't exist.

        Returns:
            bool: True if the file was successfully removed.
        """

        if path.exists(path.join(self.user_sounds_dir, filename)):
            return self.remove_file(filename, self.user_sounds_dir)
        elif path.exists(path.join(self.default_user_sounds_dir, filename)):
            raise DefaultFileRemoveAttempt(
                f"{filename} is default sound and cannot be removed!"
            )
        else:
            raise FileNotFoundError

    def remove_data(self, filename: str) -> bool:
        """
        Removes a file from the data directory.

        Args:
            filename (str): Name of the file to be removed.

        Returns:
            bool: True if the file was successfully removed.
        """

        os.remove(resolve_absolute_path(filename, DATA_DIR))
        return True

    def get_photo_directory(self, filename: str):
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
            raise FileNotFoundError

    def get_video_directory(self, filename: str):
        """
        Retrieves the directory of a specified video file.

        Args:
            filename (str): Name of the video file.

        Raises:
            FileNotFoundError: If the file doesn't exist.

        Returns:
            str: Directory path of the video file.
        """

        user_file = path.join(self.user_videos_dir, filename)
        if path.exists(user_file):
            return self.user_videos_dir
        else:
            raise FileNotFoundError

    def get_sound_directory(self, filename: str):
        """
        Retrieves the directory of a specified sound file.

        Args:
            filename (str): Name of the sound file.

        Raises:
            FileNotFoundError: If the file doesn't exist.

        Returns:
            str: Directory path of the sound file.
        """

        user_file = path.join(self.user_sounds_dir, filename)
        if path.exists(user_file):
            return self.user_sounds_dir
        elif path.exists(path.join(self.default_user_sounds_dir, filename)):
            return self.default_user_sounds_dir
        else:
            raise FileNotFoundError

    def get_music_directory(self, filename: str):
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
            raise FileNotFoundError

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
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = file.filename
        if not isinstance(filename, str):
            raise ValueError("Invalid filename.")
        file_path = os.path.join(directory, filename)
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
        return file_path

    def get_calibration_config(self):
        """
        Loads calibration settings from a configuration file.

        Returns:
            dict: Calibration settings in JSON format.
        """

        if path.exists(PICARX_CONFIG_FILE):
            calibration_settings = fileDB(PICARX_CONFIG_FILE).get_all_as_json()
            return calibration_settings
        return {}

    @staticmethod
    def get_available_models():
        """
        Recursively scans the provided directory for .tflite, .onnx and .pt model files.
        Returns a list of all found models with their full file paths.

        Returns:
            List[str]: List of paths to discovered .tflite and .pt model files.
        """

        return [
            file_to_relative(item, DATA_DIR)
            for item in get_files_with_extension(DATA_DIR, ('.tflite', '.pt', ".onnx"))
        ]
