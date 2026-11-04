import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app.api import robot_deps
from app.api.control.calibration import router
from app.schemas.autonomy.calibration import CalibrationStatus
from app.services.autonomy.calibration import CalibrationError, GuidedCalibrationService


class TestCalibrationRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.service = MagicMock(spec=GuidedCalibrationService)
        self.service.status.return_value = CalibrationStatus(
            active=True, session_id="private-token"
        )
        self.service.start = AsyncMock(
            return_value=CalibrationStatus(active=True, session_id="private-token")
        )
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[robot_deps.get_guided_calibration_service] = (
            lambda: self.service
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_public_readiness_does_not_expose_control_token(self):
        response = await self.client.get(
            "/px/api/calibration/status",
            params={"kind": "speed", "direction": "reverse", "stop_distance_m": 0.8},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["session_id"])
        self.assertTrue(response.json()["active"])
        self.service.status.assert_called_once_with(
            "speed", direction="reverse", stop_distance_m=0.8
        )

    async def test_start_returns_token_only_to_initiator(self):
        response = await self.client.post(
            "/px/api/calibration/start",
            json={"kind": "wheel_distance", "clear_path_confirmed": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session_id"], "private-token")

    async def test_expected_failures_are_actionable_conflicts(self):
        self.service.start.side_effect = CalibrationError(
            "Enable Drive encoders and wait for fresh readings."
        )
        response = await self.client.post(
            "/px/api/calibration/start", json={"kind": "wheel_distance"}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "Enable Drive encoders and wait for fresh readings.",
        )

    async def test_invalid_command_is_rejected_before_service(self):
        response = await self.client.post(
            "/px/api/calibration/private-token/heartbeat",
            json={"sequence": -1, "steering_degrees": 1000},
        )
        self.assertEqual(response.status_code, 422)
        self.service.heartbeat.assert_not_called()
