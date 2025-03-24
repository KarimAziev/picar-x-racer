from os import path
from typing import Any, Dict, Optional

from app.config.config import settings as app_config
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.managers.file_management.json_data_manager import JsonDataManager
from app.util.file_util import load_json_file

logger = Logger(name=__name__)


class SettingsService(metaclass=SingletonMeta):
    """
    Service for managing file operations related to user settings.
    """

    def __init__(
        self,
        user_settings_file=app_config.PX_SETTINGS_FILE,
        default_user_settings_file=app_config.DEFAULT_USER_SETTINGS,
        config_file=app_config.ROBOT_CONFIG_FILE,
    ):

        self.default_user_settings_file = default_user_settings_file
        self.user_settings_file = user_settings_file
        self.config_file = config_file

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

    def load_settings(self) -> Dict[str, Any]:
        """Loads user settings from a JSON file, using cache if file is not modified."""
        return self.settings_manager.load_data()

    def save_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves new settings to the user settings file.
        """
        return self.settings_manager.merge(new_settings)

    def get_calibration_config(self) -> Dict[str, Any]:
        """
        Loads calibration settings from a configuration file.

        Returns:
            Dictionary with calibration settings.
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
