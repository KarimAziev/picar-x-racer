import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from app.api import deps
from app.api.endpoints.settings import router
from app.services.domain.settings_service import SettingsService
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestPmicUserSettings(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.target = Path(self.directory.name) / "settings.json"
        template = Path(__file__).resolve().parents[3] / "user_settings.json"
        self.original = json.loads(template.read_text())
        self.original.pop("pmic", None)
        self.target.write_text(json.dumps(self.original))
        self.service = SettingsService(
            user_settings_file=str(self.target),
            default_user_settings_file=str(template),
        )
        self.connection = Mock(broadcast_json=AsyncMock())
        self.robot = Mock(refresh_robot_settings=AsyncMock())
        app = FastAPI()
        app.state.app_manager = self.connection
        app.include_router(router, prefix="/api")
        app.dependency_overrides[deps.get_settings_service] = lambda: self.service
        app.dependency_overrides[deps.get_robot_communication_service] = (
            lambda: self.robot
        )
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_existing_settings_receive_monitor_defaults(self) -> None:
        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["pmic"],
            {
                "enabled": True,
                "selected_channels": ["3V3_SYS_V", "3V3_SYS_A"],
                "refresh_seconds": 5,
            },
        )

    def test_preferences_persist_and_broadcast_without_overwriting_other_settings(
        self,
    ) -> None:
        preferences = {
            "enabled": False,
            "selected_channels": ["EXT5V_V", "VDD_CORE_A"],
            "refresh_seconds": 15,
        }
        response = self.client.post("/api/settings", json={"pmic": preferences})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["pmic"], preferences)
        persisted = json.loads(self.target.read_text())
        self.assertEqual(persisted.pop("pmic"), preferences)
        self.assertEqual(persisted, self.original)
        reloaded = SettingsService(
            user_settings_file=str(self.target),
            default_user_settings_file=str(self.target),
        )
        self.assertEqual(reloaded.load_settings()["pmic"], preferences)
        self.connection.broadcast_json.assert_awaited_once_with(
            {"type": "settings", "payload": {"pmic": preferences}}
        )
        self.robot.refresh_robot_settings.assert_awaited_once()

    def test_rejects_invalid_intervals_and_channel_names(self) -> None:
        for preferences in [
            {"refresh_seconds": 0},
            {"refresh_seconds": 301},
            {"refresh_seconds": 1.5},
            {"selected_channels": ["invalid"]},
        ]:
            with self.subTest(preferences=preferences):
                response = self.client.post("/api/settings", json={"pmic": preferences})
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(json.loads(self.target.read_text()), self.original)
        self.connection.broadcast_json.assert_not_awaited()

    def test_empty_channel_selection_is_preserved(self) -> None:
        response = self.client.post(
            "/api/settings",
            json={
                "pmic": {
                    "enabled": True,
                    "selected_channels": [],
                    "refresh_seconds": 5,
                },
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            self.client.get("/api/settings").json()["pmic"]["selected_channels"], []
        )
