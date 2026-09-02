import asyncio
import json
import math
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from app.api import robot_deps
from app.api.control.settings import _reload_autonomy_runtime
from app.control_server import app as control_app
from app.exceptions.settings import InvalidSettings
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.services.autonomy import (
    ActuationCalibration,
    AckermannOdometryService,
    HardwareController,
    LinearActuatorTranslator,
    LocalMappingService,
    MotionArbiter,
    MotionControlService,
    MotionLimits,
    SelectableDriveHardware,
    TopicBus,
    VirtualDriveHardware,
)
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


class FakeDriveHardware:
    def __init__(self) -> None:
        self.stops = 0

    def forward(self, speed: int) -> None:
        return None

    def backward(self, speed: int) -> None:
        return None

    def stop(self) -> None:
        self.stops += 1

    def set_dir_servo_angle(self, value: float) -> None:
        return None


class TestSimulationSettingsHotReload(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config_path = Path(__file__).resolve().parents[3] / "config.json"
        cls.root_config = json.loads(config_path.read_text())

    def make_configs(self) -> tuple[HardwareConfig, HardwareConfig]:
        physical_data = deepcopy(self.root_config)
        physical_data["motion_control"] = {
            "enabled": True,
            "control_frequency_hz": 20,
            "command_timeout_ms": 250,
            "max_forward_speed_mps": 1.0,
            "max_reverse_speed_mps": 0.5,
        }
        physical_data["ackermann_odometry"] = {
            "enabled": True,
            "wheelbase_m": 0.25,
            "wheel_radius_m": 0.03,
            "encoder_ticks_per_revolution": 4096,
            "gear_ratio": 1.0,
            "max_steering_age_ms": 250,
        }
        physical_data["localization_sensors"]["encoder"] = {
            "enabled": True,
            "sample_frequency_hz": 100,
            "sensors": [
                {
                    "side": "left",
                    "driver": "mock",
                    "ticks_per_sample": 2,
                }
            ],
        }
        physical_data["localization_sensors"]["lidar"] = {
            "enabled": True,
            "driver": "mock",
            "points_per_scan": 360,
            "distance_m": 1.5,
            "scan_frequency_hz": 10,
        }
        physical_data["local_mapping"] = {"enabled": True}
        simulated_data = deepcopy(physical_data)
        simulated_data["coherent_simulation"]["enabled"] = True
        simulated_data["pose_estimation"]["enabled"] = True
        return (
            HardwareConfig.model_validate(physical_data),
            HardwareConfig.model_validate(simulated_data),
        )

    async def test_switches_publishers_and_drive_route_without_restart(self) -> None:
        physical_config, simulated_config = self.make_configs()
        bus = TopicBus()
        smbus_manager = Mock()
        sensors = robot_deps.build_localization_sensor_service(
            physical_config,
            bus,
            smbus_manager,
        )
        simulation = robot_deps.build_coherent_simulation_supervisor(
            physical_config,
            bus,
        )
        pose_estimator = robot_deps.build_pose_estimator_supervisor(
            physical_config,
            bus,
        )
        odometry = AckermannOdometryService(
            bus,
            robot_deps.build_odometry_estimator(physical_config),
        )
        initial_estimator = odometry._estimator
        local_mapping = AsyncMock(spec=LocalMappingService)
        physical_drive = FakeDriveHardware()
        selector = SelectableDriveHardware(physical_drive, VirtualDriveHardware())
        controller = HardwareController(
            selector,
            LinearActuatorTranslator(
                ActuationCalibration(
                    max_forward_speed_mps=1.0,
                    max_reverse_speed_mps=0.5,
                    max_abs_steering_angle_rad=math.radians(30),
                )
            ),
        )
        motion = MotionControlService(
            MotionArbiter(
                MotionLimits(
                    max_forward_speed_mps=1.0,
                    max_reverse_speed_mps=0.5,
                    max_abs_steering_angle_rad=math.radians(30),
                )
            ),
            controller,
            topic_bus=bus,
            drive_hardware=selector,
        )
        await sensors.start()
        await simulation.start()
        await pose_estimator.start()
        odometry.start()
        try:
            await _reload_autonomy_runtime(
                physical_config,
                simulated_config,
                sensors,
                bus,
                smbus_manager,
                None,
                odometry,
                motion,
                None,
                local_mapping,
                simulation,
                pose_estimator,
            )
            await asyncio.sleep(0.02)

            self.assertTrue(selector.simulation_enabled)
            self.assertTrue(simulation.running)
            self.assertTrue(pose_estimator.running)
            self.assertIsNot(odometry._estimator, initial_estimator)
            local_mapping.reconfigure_from.assert_awaited_once()
            simulated_status = {item.sensor: item for item in sensors.status.sensors}
            self.assertGreater(simulated_status["lidar"].published_messages, 0)
            self.assertGreater(simulated_status["encoder"].published_messages, 0)
            first_simulation_service = simulation.service

            changed_data = simulated_config.model_dump(mode="json")
            changed_data["coherent_simulation"]["world_scenario"] = "corridor"
            changed_data["coherent_simulation"]["sensor_imperfections"][
                "enabled"
            ] = True
            changed_data["coherent_simulation"]["sensor_imperfections"][
                "random_seed"
            ] = 2026
            changed_simulated_config = HardwareConfig.model_validate(changed_data)
            await _reload_autonomy_runtime(
                simulated_config,
                changed_simulated_config,
                sensors,
                bus,
                smbus_manager,
                None,
                odometry,
                motion,
                None,
                local_mapping,
                simulation,
                pose_estimator,
            )

            self.assertIsNot(simulation.service, first_simulation_service)
            self.assertEqual(simulation.service.world.scenario, "corridor")  # type: ignore[union-attr]
            self.assertTrue(
                simulation.service.sensor_imperfections.enabled  # type: ignore[union-attr]
            )
            self.assertEqual(
                simulation.service.sensor_imperfections.random_seed,  # type: ignore[union-attr]
                2026,
            )
            self.assertEqual(local_mapping.reconfigure_from.await_count, 2)

            await _reload_autonomy_runtime(
                changed_simulated_config,
                physical_config,
                sensors,
                bus,
                smbus_manager,
                None,
                odometry,
                motion,
                None,
                local_mapping,
                simulation,
                pose_estimator,
            )

            self.assertFalse(selector.simulation_enabled)
            self.assertFalse(simulation.enabled)
            self.assertFalse(pose_estimator.enabled)
            self.assertEqual(local_mapping.reconfigure_from.await_count, 3)
            physical_status = {item.sensor: item for item in sensors.status.sensors}
            self.assertTrue(physical_status["encoder"].running)
        finally:
            await pose_estimator.stop()
            await simulation.stop()
            await odometry.stop()
            await sensors.stop()


if __name__ == "__main__":
    unittest.main()
