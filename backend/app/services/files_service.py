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
    - get_audio_file_details: Retrieves details (track name and duration) of a specific audio file.
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
from os import environ, path
from typing import Any, Dict, List

from app.adapters.robot_hat.filedb import fileDB
from app.config.paths import (
    CONFIG_USER_DIR,
    DEFAULT_MUSIC_DIR,
    DEFAULT_SOUND_DIR,
    DEFAULT_USER_SETTINGS,
    PICARX_CONFIG_FILE,
)
from app.exceptions.file_exceptions import DefaultFileRemoveAttempt
from app.services.audio_service import AudioService
from app.util.file_util import ensure_parent_dir_exists, load_json_file
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
        self.user = os.getlogin()
        self.user_home = path.expanduser(f"~{self.user}")
        self.logger = Logger(name=__name__)
        self.user_settings_file = path.join(
            CONFIG_USER_DIR, "picar-x-racer", "user_settings.json"
        )
        self.user_photos_dir = environ.get(
            "PHOTOS_PATH", "%s/Pictures/picar-x-racer/" % self.user_home
        )
        self.user_sounds_dir = environ.get(
            "SOUNDS_PATH", "%s/Music/picar-x-racer/sounds/" % self.user_home
        )
        self.user_music_dir = environ.get(
            "MUSIC_PATH", "%s/Music/picar-x-racer/music/" % self.user_home
        )
        self.audio_manager = audio_manager

        self.cache = {}
        self.cached_settings = None
        self.last_modified_time = None
        self.current_settings_file = None
        self.settings = self.load_settings()
        self.list_all_music_with_details()

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
            self.logger.info(f"Using cached settings from {self.current_settings_file}")

        return self.cached_settings

    def save_settings(self, new_settings: Dict[str, Any]):
        """Saves new settings to the user settings file."""
        existing_settings = self.load_settings()
        self.logger.info(f"Saving settings to {self.user_settings_file}")
        merged_settings = {
            **existing_settings,
            **new_settings,
        }
        ensure_parent_dir_exists(self.user_settings_file)

        with open(self.user_settings_file, "w") as settings_file:
            json.dump(merged_settings, settings_file, indent=2)

        self.settings = merged_settings
        self.logger.debug(f"settings saved to {self.user_settings_file}")
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

    def list_all_music_with_details(self):
        """Lists all music files with details including whether they are removable."""
        defaults = self.list_default_music(full=True)
        user_music = self.list_user_music(full=True)
        result = []

        for file in defaults:
            details = self.get_audio_file_details_cached(file)
            if details:
                details["removable"] = False
                result.append(details)

        for file in user_music:
            details = self.get_audio_file_details_cached(file)
            if details:
                details["removable"] = True
                result.append(details)

        return result

    def get_audio_file_details_cached(self, file: str):
        """
        Gets cached details of an audio file such as track name and duration.

        Args:
            file (str): File path of the audio file.

        Returns:
            dict: A dictionary with track name and duration.
        """
        file_mod_time = os.path.getmtime(file)

        cache_key = (file, file_mod_time)

        if cache_key in self.cache:
            self.logger.info(f"Using cached details for {file}")
            return self.cache[cache_key]
        else:
            details = self.get_audio_file_details(file)
            if details:
                self.cache[cache_key] = details
            return details

    def get_audio_file_details(self, file):
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

    def remove_photo(self, filename: str):
        """
        Removes a photo file from the user's photo directory.

        Args:
            filename (str): Name of the photo file to be removed.

        Returns:
            bool: True if the file was successfully removed.
        """

        return self.remove_file(filename, self.user_photos_dir)

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

        self.logger.info(f"removing music file {filename}")
        if path.exists(path.join(self.user_music_dir, filename)):
            return self.remove_file(filename, self.user_music_dir)
        elif path.exists(path.join(self.default_user_music_dir, filename)):
            raise DefaultFileRemoveAttempt(
                f"{filename} is default music and cannot be removed!"
            )
        else:
            raise FileNotFoundError

    def remove_sound(self, filename: str):
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
