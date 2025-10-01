from typing import Any, Dict

from app.config.config import settings as app_config
from app.core.logger import Logger
from app.managers.file_management.json_data_manager import JsonDataManager

_log = Logger(name=__name__)


class SettingsService:
    """
    Service for managing file operations related to user settings.
    """

    def __init__(
        self,
        user_settings_file=app_config.PX_SETTINGS_FILE,
        default_user_settings_file=app_config.DEFAULT_USER_SETTINGS,
        config_file=app_config.ROBOT_CONFIG_FILE,
    ) -> None:

        self._default_user_settings_file = default_user_settings_file
        self._user_settings_file = user_settings_file
        self._config_file = config_file

        self._settings_manager = JsonDataManager(
            target_file=self._user_settings_file,
            template_file=self._default_user_settings_file,
        )
        self._settings_manager.on(
            self._settings_manager.UPDATE_EVENT, self._reload_settings
        )

        self._settings_manager.on(
            self._settings_manager.LOAD_EVENT, self._reload_settings
        )
        self.settings: Dict[str, Any] = self._settings_manager.load_data()

    def _reload_settings(self, data: Dict[str, Any]) -> None:
        _log.debug("Refreshing settings")
        self.settings = data

    def load_settings(self) -> Dict[str, Any]:
        """Loads user settings from a JSON file, using cache if file is not modified."""
        _log.debug("Loading settings")
        return self._settings_manager.load_data()

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves new settings to the user settings file.
        """
        return self._settings_manager.merge(new_settings)
