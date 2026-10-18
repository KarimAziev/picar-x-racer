import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
import unittest
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from robot_hat.i2c.smbus_manager import SMBusManager

from app.api import robot_deps
from app.api.control.sensors import router
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.robot.config import HardwareConfig
from app.services.autonomy.sensor_publishers import LocalizationSensorService
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import STEERING_POSITION, STEERING_STATE


class SteeringTelemetryApiTests(unittest.TestCase):
    def test_sensor_status_and_default_stream_without_motion_control(self) -> None:
        config = HardwareConfig.model_validate_json(
            (Path(__file__).parents[4] / "config.json").read_text()
        )
        data = config.model_dump()
        data["localization_sensors"]["steering"] = {
            "enabled": True,
            "driver": "mock",
            "initial_angle_degrees": 190.0,
            "center_angle_deg": 180.0,
        }
        config = HardwareConfig.model_validate(data)
        self.assertFalse(config.motion_control.enabled)
        bus = TopicBus()
        service = robot_deps.build_steering_feedback_service(
            config, Mock(spec=SMBusManager), topic_bus=bus
        )
        assert service is not None
        manager = Mock(spec=JsonDataManager)
        manager.load_data.return_value = data
        sensors = LocalizationSensorService({}, enabled_sensors=())

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncIterator[None]:
            app.state.steering_feedback_service = service
            subscription = bus.subscribe(STEERING_POSITION)
            await service.start()
            await asyncio.wait_for(subscription.get(), timeout=1)
            subscription.close()
            try:
                yield
            finally:
                await service.stop()
                bus.close()

        app = FastAPI(lifespan=lifespan)
        app.include_router(router)
        app.dependency_overrides[robot_deps.get_config_manager] = lambda: manager
        app.dependency_overrides[robot_deps.get_localization_sensor_service] = (
            lambda: sensors
        )
        app.dependency_overrides[robot_deps.get_robot_topic_bus] = lambda: bus
        with TestClient(app) as client:
            response = client.get("/px/api/sensors/status")
            self.assertEqual(response.status_code, 200)
            status = {item["sensor"]: item for item in response.json()["sensors"]}
            self.assertTrue(status["steering"]["enabled"])
            self.assertTrue(status["steering"]["running"])
            self.assertGreater(status["steering"]["published_messages"], 0)
            self.assertIsNone(status["steering"]["error"])
            self.assertFalse(status["encoder"]["enabled"])
            with client.websocket_connect("/px/ws/telemetry") as websocket:
                message = websocket.receive_json()
                self.assertEqual(message["channel"], "steering")
                self.assertEqual(message["topic"], "/steering/position")
                self.assertEqual(message["payload"]["sensor_angle_deg"], 190.0)
                websocket.close()

                async def wait_for_disconnect() -> None:
                    async with asyncio.timeout(1):
                        while bus.stats(STEERING_POSITION).subscribers:
                            await asyncio.sleep(0.01)

                assert client.portal is not None
                client.portal.call(wait_for_disconnect)
            self.assertIsNone(bus.latest(STEERING_STATE))

            data["localization_sensors"]["steering"]["enabled"] = False
            status = client.get("/px/api/sensors/status").json()["sensors"][-1]
            self.assertFalse(status["enabled"])
            self.assertFalse(status["running"])
