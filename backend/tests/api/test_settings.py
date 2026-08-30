import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from app.api import robot_deps
from app.control_server import app as control_app
from app.exceptions.settings import InvalidSettings
from app.schemas.robot.config import PartialHardwareConfig
from app.services.connection_service import ConnectionService
from app.services.control.settings_service import SettingsService
from fastapi.testclient import TestClient
from pydantic import ValidationError


class TestPartialRobotSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config_path = Path(__file__).resolve().parents[3] / "config.json"
        with config_path.open() as config_file:
            cls.config = json.load(config_file)

    def setUp(self) -> None:
        self.settings_service = Mock(spec=SettingsService)
        self.settings_service.merge_settings.side_effect = lambda settings: settings
        self.connection_service = Mock(spec=ConnectionService)
        self.connection_service.broadcast_json = AsyncMock()
        control_app.dependency_overrides[robot_deps.get_robot_settings_service] = (
            lambda: self.settings_service
        )
        control_app.dependency_overrides[robot_deps.get_connection_manager] = (
            lambda: self.connection_service
        )
        self.client = TestClient(control_app)

    def tearDown(self) -> None:
        control_app.dependency_overrides.clear()

    def test_accepts_camera_pan_servo_without_batteries(self) -> None:
        response = self.client.patch(
            "/px/api/settings/config",
            json={"cam_pan_servo": self.config["cam_pan_servo"]},
        )

        self.assertEqual(response.status_code, 200, response.text)
        submitted = self.settings_service.merge_settings.call_args.args[0]
        self.assertEqual(submitted.model_fields_set, {"cam_pan_servo"})
        self.connection_service.broadcast_json.assert_awaited_once()

    def test_rejects_explicit_null_batteries(self) -> None:
        with self.assertRaisesRegex(ValidationError, "Batteries must be a list"):
            PartialHardwareConfig.model_validate({"batteries": None})

        response = self.client.patch(
            "/px/api/settings/config", json={"batteries": None}
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.settings_service.merge_settings.assert_not_called()

    def test_reports_partial_hardware_configuration_conflict(self) -> None:
        self.settings_service.merge_settings.side_effect = InvalidSettings(
            "Conflicting configurations for shared PWM device"
        )

        response = self.client.patch(
            "/px/api/settings/config",
            json={"cam_pan_servo": self.config["cam_pan_servo"]},
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("Conflicting configurations", response.json()["detail"])
        self.connection_service.broadcast_json.assert_not_awaited()

    def test_reports_full_hardware_initialization_failure(self) -> None:
        self.settings_service.save_settings.side_effect = InvalidSettings(
            "Unable to apply hardware settings: device offline"
        )

        response = self.client.put(
            "/px/api/settings/config",
            json=self.config,
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("device offline", response.json()["detail"])
        self.connection_service.broadcast_json.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
