from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
from typing import AsyncIterator
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import robot_deps
from app.api.control.recordings import router
from app.managers.file_management.json_data_manager import JsonDataManager
from app.services.autonomy.recording import AutonomyRecorder
from app.services.autonomy.topic_bus import TopicBus


class RecordingApiTests(unittest.TestCase):
    def test_record_stop_download_and_path_validation_use_isolated_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bus = TopicBus()
            recorder = AutonomyRecorder(bus, Path(directory))
            config = Mock(spec=JsonDataManager)
            config.load_data.return_value = {"schema_version": 7}

            @asynccontextmanager
            async def lifespan(app: FastAPI) -> AsyncIterator[None]:
                yield
                await recorder.stop()
                bus.close()

            app = FastAPI(lifespan=lifespan)
            app.include_router(router)
            app.dependency_overrides[robot_deps.get_autonomy_recorder] = (
                lambda: recorder
            )
            app.dependency_overrides[robot_deps.get_config_manager] = lambda: config
            with patch(
                "app.api.control.recordings.software_versions",
                return_value={"git_commit": "test"},
            ), TestClient(app) as client:
                started = client.post("/px/api/autonomy/recordings/start")
                self.assertEqual(started.status_code, 200)
                session = started.json()["session_id"]
                self.assertEqual(
                    client.post("/px/api/autonomy/recordings/start").status_code, 409
                )
                self.assertEqual(
                    client.get(
                        f"/px/api/autonomy/recordings/{session}/download"
                    ).status_code,
                    409,
                )
                self.assertFalse(
                    client.post("/px/api/autonomy/recordings/stop").json()["active"]
                )
                downloaded = client.get(
                    f"/px/api/autonomy/recordings/{session}/download"
                )
                self.assertEqual(downloaded.status_code, 200)
                self.assertIn('"format_version":1', downloaded.text)
                self.assertEqual(
                    client.get(
                        "/px/api/autonomy/recordings/not-a-session/download"
                    ).status_code,
                    404,
                )
                self.assertEqual(
                    client.get(
                        f"/px/api/autonomy/recordings/{'0' * 32}/download"
                    ).status_code,
                    404,
                )
                second = client.post("/px/api/autonomy/recordings/start")
                self.assertNotEqual(second.json()["session_id"], session)
            self.assertFalse(recorder.status.active)
