import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.api.robot_deps import (
    get_localization_sensor_service,
    get_steering_feedback_service,
)
from app.managers.file_management.json_data_manager import JsonDataManager
from app.services.autonomy import TopicBus
from app.services.autonomy.topics import ENCODER_STATE, IMU_DATA, LIDAR_SCAN


class TestLocalizationMockMode(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        get_localization_sensor_service.cache_clear()
        get_steering_feedback_service.cache_clear()

    async def asyncTearDown(self) -> None:
        get_localization_sensor_service.cache_clear()
        get_steering_feedback_service.cache_clear()

    async def test_mock_configuration_runs_real_publishers(self) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        data = json.loads(root_config.read_text())
        data["localization_sensors"] = {
            "lidar": {
                "enabled": True,
                "driver": "mock",
                "points_per_scan": 36,
                "min_measurements_per_scan": 8,
                "scan_frequency_hz": 30,
                "distance_m": 2.5,
            },
            "imu": {
                "enabled": True,
                "driver": "mock",
                "sample_frequency_hz": 100,
                "angular_velocity_radps": [0.0, 0.0, 0.2],
            },
            "encoder": {
                "enabled": True,
                "sample_frequency_hz": 100,
                "sensors": [
                    {
                        "side": "left",
                        "driver": "mock",
                        "ticks_per_sample": 3,
                    },
                    {
                        "side": "right",
                        "driver": "mock",
                        "ticks_per_sample": 5,
                    },
                ],
            },
            "steering": {
                "enabled": True,
                "driver": "mock",
                "initial_angle_degrees": 185.0,
                "center_angle_deg": 180.0,
                "sample_frequency_hz": 100,
            },
        }
        bus = TopicBus()
        lidar_output = bus.subscribe(LIDAR_SCAN, replay_latest=False)
        imu_output = bus.subscribe(IMU_DATA, replay_latest=False)
        encoder_output = bus.subscribe(
            ENCODER_STATE,
            max_queue_size=4,
            replay_latest=False,
        )
        smbus_manager = MagicMock()
        config_manager = MagicMock(spec=JsonDataManager)
        config_manager.load_data.return_value = data
        service = get_localization_sensor_service(
            config_manager,
            bus,
            smbus_manager,
        )
        steering_service = get_steering_feedback_service(config_manager)
        self.assertIsNotNone(steering_service)
        assert steering_service is not None

        await steering_service.start()
        await service.start()
        try:
            lidar = await asyncio.wait_for(lidar_output.get(), timeout=1)
            imu = await asyncio.wait_for(imu_output.get(), timeout=1)
            await asyncio.wait_for(encoder_output.get(), timeout=1)
            encoder = await asyncio.wait_for(encoder_output.get(), timeout=1)
            for _attempt in range(20):
                if steering_service.latest is not None:
                    break
                await asyncio.sleep(0.005)
            steering = steering_service.latest
        finally:
            await service.stop()
            await steering_service.stop()

        self.assertEqual(lidar.ranges_m[0], 2.5)
        self.assertEqual(imu.angular_velocity_z_radps, 0.2)
        self.assertEqual(encoder.mean_delta_ticks, 4)
        self.assertIsNotNone(steering)
        assert steering is not None
        self.assertAlmostEqual(steering.wheel_angle_rad, 0.0872664626)
        self.assertIsNone(steering_service.latest)
        self.assertEqual(
            {status.sensor: status.enabled for status in service.status.sensors},
            {"lidar": True, "imu": True, "encoder": True},
        )
        smbus_manager.get_bus.assert_not_called()


if __name__ == "__main__":
    unittest.main()
