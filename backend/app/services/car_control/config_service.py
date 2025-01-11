import json
import os
from typing import Any, Dict, Optional

from app.config.config import settings as app_config
from app.core.logger import Logger
from app.util.atomic_write import atomic_write
from app.util.file_util import load_json_file


class ConfigService:
    """
    Service for managing file operations related to robot settings.
    """

    def __init__(
        self,
        user_settings_file=app_config.ROBOT_CONFIG_FILE,
        default_user_settings_file=app_config.DEFAULT_ROBOT_CONFIG_FILE,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._logger = Logger(name=__name__)

        self.user_settings_file = user_settings_file
        self.default_user_settings_file = default_user_settings_file

        self.cache: Optional[Dict[str, Any]] = None

        self.last_modified_time = None
        self.current_settings_file = None
        self.settings: Dict[str, Any] = self.load_settings()

    def get_settings_file(self) -> str:
        """
        Determines the current settings file to use.
        """
        return (
            self.user_settings_file
            if os.path.exists(self.user_settings_file)
            else self.default_user_settings_file
        )

    def load_settings(self) -> Dict[str, Any]:
        """
        Loads user settings from a JSON file, using cache if file is not modified.
        """
        settings_file = self.get_settings_file()

        try:
            current_modified_time = os.path.getmtime(settings_file)
        except OSError:
            current_modified_time = None

        if (
            not hasattr(self, 'cached_settings')
            or self.cached_settings is None
            or self.last_modified_time != current_modified_time
            or self.current_settings_file != settings_file
        ):
            self._logger.info(f"Loading settings from {settings_file}")
            self.cached_settings: Dict[str, Any] = load_json_file(settings_file)
            self.last_modified_time = current_modified_time
            self.current_settings_file = settings_file
        else:
            self._logger.debug(
                f"Using cached settings from {self.current_settings_file}"
            )

        return self.cached_settings

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves new settings to the user settings file.
        """
        existing_settings = self.load_settings()

        self._logger.info(f"Saving settings to {self.user_settings_file}")

        merged_settings = {
            **existing_settings,
            **new_settings,
        }
        self._logger.debug("New settings %s", new_settings)
        self._logger.debug("Merged settings %s", merged_settings)
        with atomic_write(self.user_settings_file) as tmp:
            json.dump(merged_settings, tmp, indent=2)
        self.settings = merged_settings
        self._logger.info("Settings saved to %s", self.user_settings_file)
        return self.settings
