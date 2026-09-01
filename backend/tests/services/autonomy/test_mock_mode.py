import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from app.api.robot_deps import (
    build_coherent_simulation_supervisor,
    build_localization_sensor_service,
    get_localization_sensor_service,
    get_steering_feedback_service,
)
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.robot.config import HardwareConfig
from app.services.autonomy import TopicBus
from app.services.autonomy.topics import ENCODER_STATE, IMU_DATA, LIDAR_SCAN
from robot_hat import MockAngularPosition, MockEncoder, QuadratureDecodeMode


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
        steering_service = get_steering_feedback_service(config_manager, smbus_manager)
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

    async def test_coherent_simulation_replaces_lidar_imu_and_encoder_drivers(
        self,
    ) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        data = json.loads(root_config.read_text())
        data["motion_control"] = {
            "enabled": True,
            "control_frequency_hz": 20,
            "command_timeout_ms": 250,
            "max_forward_speed_mps": 1.0,
            "max_reverse_speed_mps": 0.5,
        }
        data["ackermann_odometry"] = {
            "enabled": True,
            "wheelbase_m": 0.25,
            "wheel_radius_m": 0.03,
            "encoder_ticks_per_revolution": 4096,
            "gear_ratio": 1.0,
            "max_steering_age_ms": 250,
        }
        data["coherent_simulation"]["enabled"] = True
        data["localization_sensors"]["lidar"] = {
            "enabled": True,
            "driver": "mock",
            "points_per_scan": 36,
            "angular_resolution_deg": 10,
            "min_measurements_per_scan": 8,
        }
        config = HardwareConfig.model_validate(data)
        bus = TopicBus()
        smbus_manager = MagicMock()
        with patch("app.api.robot_deps.MockLidar2D") as mock_lidar:
            sensors = build_localization_sensor_service(config, bus, smbus_manager)
            simulation = build_coherent_simulation_supervisor(config, bus)
            statuses = {item.sensor: item for item in sensors.status.sensors}

            await sensors.start()
            await simulation.start()
            try:
                for _attempt in range(20):
                    statuses = {item.sensor: item for item in sensors.status.sensors}
                    if all(
                        statuses[name].published_messages > 0
                        for name in ("lidar", "imu", "encoder")
                    ):
                        break
                    await asyncio.sleep(0.005)
            finally:
                await simulation.stop()
                await sensors.stop()

            mock_lidar.assert_not_called()

        self.assertTrue(statuses["lidar"].enabled)
        self.assertTrue(statuses["imu"].enabled)
        self.assertTrue(statuses["encoder"].enabled)
        self.assertGreater(statuses["lidar"].published_messages, 0)
        self.assertGreater(statuses["imu"].published_messages, 0)
        self.assertGreater(statuses["encoder"].published_messages, 0)
        smbus_manager.get_bus.assert_not_called()

    async def test_as5600l_factories_share_managed_i2c_bus(self) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        data = json.loads(root_config.read_text())
        data["localization_sensors"] = {
            "lidar": {"enabled": False, "driver": "rplidar_c1"},
            "imu": {"enabled": False, "driver": "sh3001"},
            "encoder": {
                "enabled": True,
                "sample_frequency_hz": 100,
                "sensors": [
                    {
                        "side": "left",
                        "driver": "as5600l",
                        "bus": 1,
                        "address": "0x40",
                    }
                ],
            },
            "steering": {
                "enabled": True,
                "driver": "as5600l",
                "bus": 1,
                "address": "0x41",
            },
        }
        bus = TopicBus()
        output = bus.subscribe(ENCODER_STATE, replay_latest=False)
        managed_bus = MagicMock()
        smbus_manager = MagicMock()
        smbus_manager.get_bus.return_value = managed_bus
        config_manager = MagicMock(spec=JsonDataManager)
        config_manager.load_data.return_value = data

        with patch(
            "app.api.robot_deps.AS5600LEncoder",
            return_value=MockEncoder(ticks_per_sample=2),
        ) as encoder_type, patch(
            "app.api.robot_deps.AS5600LAngularPosition",
            return_value=MockAngularPosition(initial_angle_degrees=185.0),
        ) as steering_type:
            service = get_localization_sensor_service(
                config_manager, bus, smbus_manager
            )
            steering_service = get_steering_feedback_service(
                config_manager, smbus_manager
            )
            self.assertIsNotNone(steering_service)
            assert steering_service is not None
            await steering_service.start()
            await service.start()
            try:
                state = await asyncio.wait_for(output.get(), timeout=1)
            finally:
                await service.stop()
                await steering_service.stop()

        self.assertIsNotNone(state.left)
        encoder_type.assert_called_once_with(
            bus=managed_bus,
            address=0x40,
            invert_direction=False,
            max_sample_gap_ns=100_000_000,
            max_abs_speed_rps=5.0,
        )
        steering_type.assert_called_once_with(bus=managed_bus, address=0x41)
        self.assertEqual(smbus_manager.get_bus.call_args_list, [call(1), call(1)])

    async def test_gpio_quadrature_factory_builds_owned_backend(self) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        data = json.loads(root_config.read_text())
        data["localization_sensors"]["encoder"] = {
            "enabled": True,
            "sample_frequency_hz": 100,
            "sensors": [
                {
                    "side": "right",
                    "driver": "gpio_quadrature",
                    "a_pin": 17,
                    "b_pin": "GPIO27",
                    "decode_mode": "x2",
                    "pull_up": True,
                    "invert_direction": True,
                }
            ],
        }
        bus = TopicBus()
        output = bus.subscribe(ENCODER_STATE, replay_latest=False)
        smbus_manager = MagicMock()
        config_manager = MagicMock(spec=JsonDataManager)
        config_manager.load_data.return_value = data

        with patch("app.api.robot_deps.GPIOZeroDigitalEdgeInput") as input_type, patch(
            "app.api.robot_deps.GPIOQuadratureCounterBackend"
        ) as backend_type, patch(
            "app.api.robot_deps.QuadratureEncoder",
            return_value=MockEncoder(ticks_per_sample=-4),
        ) as encoder_type:
            service = get_localization_sensor_service(
                config_manager, bus, smbus_manager
            )
            await service.start()
            try:
                state = await asyncio.wait_for(output.get(), timeout=1)
            finally:
                await service.stop()

        self.assertIsNotNone(state.right)
        self.assertEqual(
            input_type.call_args_list,
            [
                call(17, pull_up=True, active_state=None),
                call("GPIO27", pull_up=True, active_state=None),
            ],
        )
        backend_type.assert_called_once_with(
            a_input=input_type.return_value,
            b_input=input_type.return_value,
            decode_mode=QuadratureDecodeMode.X2,
        )
        encoder_type.assert_called_once_with(
            backend=backend_type.return_value,
            invert_direction=True,
        )


if __name__ == "__main__":
    unittest.main()
