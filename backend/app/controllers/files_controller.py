import json
import os
from os import environ, path
from typing import List
from app.util.logger import Logger
from app.config.paths import PICARX_CONFIG_FILE
from app.robot_hat.filedb import fileDB
from app.util.file_util import load_json_file, ensure_parent_dir_exists
from app.exceptions.file_controller import DefaultFileRemoveAttempt
from app.config.paths import (
    DEFAULT_MUSIC_DIR,
    CONFIG_USER_DIR,
    DEFAULT_SOUND_DIR,
    DEFAULT_USER_SETTINGS,
)

from werkzeug.datastructures import FileStorage


class FilesController(Logger):
    default_user_settings_file = DEFAULT_USER_SETTINGS
    default_user_music_dir = DEFAULT_MUSIC_DIR
    default_user_sounds_dir = DEFAULT_SOUND_DIR

    def __init__(self, *args, **kwargs):
        super().__init__(name="FilesController", *args, **kwargs)
        self.user = os.getlogin()
        self.user_home = path.expanduser(f"~{self.user}")
        self.user_settings_file = path.join(CONFIG_USER_DIR, "user_settings.json")
        self.user_photos_dir = environ.get(
            "PHOTOS_PATH", "%s/Pictures/picar-x-racer/" % self.user_home
        )
        self.user_sounds_dir = environ.get(
            "SOUNDS_PATH", "%s/Music/picar-x-racer/sounds/" % self.user_home
        )
        self.user_music_dir = environ.get(
            "MUSIC_PATH", "%s/Music/picar-x-racer/music/" % self.user_home
        )

        self.settings = self.load_settings()

    def load_settings(self):
        settings_file = (
            self.user_settings_file
            if os.path.exists(self.user_settings_file)
            else FilesController.default_user_settings_file
        )
        self.info(f"loading_settings {settings_file}")
        return load_json_file(settings_file)

    def save_settings(self, new_settings):
        existing_settings = self.load_settings()
        self.info(f"saving settings to {self.user_settings_file}")
        merged_settings = {
            **existing_settings,
            **new_settings,
        }
        ensure_parent_dir_exists(self.user_settings_file)

        with open(self.user_settings_file, "w") as settings_file:
            json.dump(merged_settings, settings_file, indent=2)

        self.settings = merged_settings
        self.debug(f"settings saved to {self.user_settings_file}")
        return self.settings

    def list_files(self, directory: str) -> List[str]:
        """
        Lists all files in the specified directory.
        """
        if not os.path.exists(directory):
            return []

        files = []
        for file in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, file)):
                files.append(file)
        return files

    def list_default_music(self):
        return self.list_files(self.default_user_music_dir)

    def list_default_sounds(self):
        return self.list_files(self.default_user_sounds_dir)

    def list_user_photos(self) -> List[str]:
        """
        Lists user photos.
        """
        return self.list_files(self.user_photos_dir)

    def list_user_music(self) -> List[str]:
        return self.list_files(self.user_music_dir)

    def list_user_sounds(self) -> List[str]:
        return self.list_files(self.user_sounds_dir)

    def remove_file(self, file: str, directory: str):
        """
        Remove file if in directory.
        """

        full_name = os.path.join(directory, file)

        os.remove(full_name)
        return True

    def save_sound(self, file: FileStorage) -> str:
        """
        Saves the uploaded file to the user's sound directory.
        """
        return self.save_uploaded_file(file, self.user_sounds_dir)

    def save_music(self, file: FileStorage) -> str:
        """
        Saves the uploaded file to the user's music directory.
        """
        return self.save_uploaded_file(file, self.user_music_dir)

    def save_photo(self, file: FileStorage) -> str:
        """
        Saves the uploaded file to the user's photos directory.
        """
        return self.save_uploaded_file(file, self.user_photos_dir)

    def remove_photo(self, filename: str):
        return self.remove_file(filename, self.user_photos_dir)

    def remove_music(self, filename: str):
        if path.exists(path.join(self.user_music_dir, filename)):
            return self.remove_file(self.user_music_dir, filename)
        elif path.exists(path.join(self.default_user_music_dir, filename)):
            raise DefaultFileRemoveAttempt(
                f"{filename} is default music and cannot be removed!"
            )
        else:
            raise FileNotFoundError

    def remove_sound(self, filename: str):
        return self.remove_file(filename, self.user_sounds_dir)

    def get_photo_directory(self, filename: str):
        user_file = path.join(self.user_photos_dir, filename)
        if path.exists(user_file):
            return self.user_photos_dir
        else:
            raise FileNotFoundError

    def get_sound_directory(self, filename: str):
        user_file = path.join(self.user_sounds_dir, filename)
        if path.exists(user_file):
            return self.user_sounds_dir
        elif path.exists(path.join(self.default_user_sounds_dir, filename)):
            return self.default_user_sounds_dir
        else:
            raise FileNotFoundError

    def get_music_directory(self, filename: str):
        user_file = path.join(self.user_music_dir, filename)
        if path.exists(user_file):
            return user_file
        elif path.exists(path.join(self.default_user_music_dir, filename)):
            return self.default_user_music_dir
        else:
            raise FileNotFoundError

    def save_uploaded_file(self, file: FileStorage, directory: str) -> str:
        """
        Saves uploaded file to the specified directory.
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = file.filename
        if not isinstance(filename, str):
            raise ValueError("Invalid filename.")
        file_path = os.path.join(directory, filename)
        file.save(file_path)
        return file_path

    def get_calibration_config(self):
        if path.exists(PICARX_CONFIG_FILE):
            calibration_settings = fileDB(PICARX_CONFIG_FILE).get_all_as_json()
            return calibration_settings
        return {}
