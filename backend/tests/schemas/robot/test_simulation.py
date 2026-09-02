import json
import unittest
from copy import deepcopy
from pathlib import Path

from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.schemas.robot.simulation import CoherentSimulationConfig
from pydantic import ValidationError


class TestCoherentSimulationConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        cls.root_data = json.loads(root_config.read_text())

    def simulation_ready_data(self) -> dict:
        data = deepcopy(self.root_data)
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
        data["localization_sensors"]["encoder"] = {
            "enabled": False,
            "sensors": [],
        }
        data["coherent_simulation"] = {
            "enabled": True,
            "update_frequency_hz": 100,
            "command_timeout_ms": 250,
            "initial_x_m": 1.0,
            "initial_y_m": -2.0,
            "initial_yaw_rad": 0.5,
        }
        return data

    def test_missing_simulation_block_keeps_existing_configuration_valid(self) -> None:
        data = deepcopy(self.root_data)
        data.pop("coherent_simulation", None)

        config = HardwareConfig.model_validate(data)

        self.assertFalse(config.coherent_simulation.enabled)

    def test_partial_odometry_update_does_not_require_sensor_section(self) -> None:
        partial = PartialHardwareConfig.model_validate(
            {
                "ackermann_odometry": {
                    "enabled": True,
                    "wheelbase_m": 0.25,
                    "wheel_radius_m": 0.03,
                    "encoder_ticks_per_revolution": 4096,
                }
            }
        )

        self.assertTrue(partial.ackermann_odometry.enabled)

    def test_simulation_can_supply_encoder_input_for_odometry(self) -> None:
        config = HardwareConfig.model_validate(self.simulation_ready_data())

        self.assertTrue(config.coherent_simulation.enabled)
        self.assertFalse(config.localization_sensors.encoder.enabled)
        self.assertTrue(config.ackermann_odometry.enabled)

    def test_simulation_requires_motion_control(self) -> None:
        data = self.simulation_ready_data()
        data["motion_control"]["enabled"] = False
        data["motion_control"]["max_forward_speed_mps"] = None
        data["motion_control"]["max_reverse_speed_mps"] = None

        with self.assertRaisesRegex(ValidationError, "requires motion control"):
            HardwareConfig.model_validate(data)

    def test_simulation_requires_ackermann_odometry(self) -> None:
        data = self.simulation_ready_data()
        data["ackermann_odometry"]["enabled"] = False
        data["ackermann_odometry"]["wheelbase_m"] = None
        data["ackermann_odometry"]["wheel_radius_m"] = None
        data["ackermann_odometry"]["encoder_ticks_per_revolution"] = None

        with self.assertRaisesRegex(ValidationError, "requires Ackermann odometry"):
            HardwareConfig.model_validate(data)

    def test_watchdog_must_cover_two_simulation_updates(self) -> None:
        with self.assertRaisesRegex(ValidationError, "at least two update cycles"):
            CoherentSimulationConfig(
                enabled=True,
                update_frequency_hz=10,
                command_timeout_ms=100,
            )

    def test_world_defaults_keep_old_configuration_compatible(self) -> None:
        config = HardwareConfig.model_validate(self.simulation_ready_data())

        self.assertEqual(config.coherent_simulation.world_scenario, "single_obstacle")
        self.assertEqual(config.coherent_simulation.world_width_m, 6)
        self.assertEqual(config.coherent_simulation.lidar_scan_frequency_hz, 10)
        self.assertFalse(config.coherent_simulation.sensor_imperfections.enabled)
        self.assertEqual(
            config.coherent_simulation.sensor_imperfections.random_seed,
            7,
        )

    def test_sensor_imperfections_validate_probability_and_noise(self) -> None:
        with self.assertRaises(ValidationError):
            CoherentSimulationConfig.model_validate(
                {"sensor_imperfections": {"lidar_dropout_probability": 1.1}}
            )
        with self.assertRaises(ValidationError):
            CoherentSimulationConfig.model_validate(
                {"sensor_imperfections": {"encoder_noise_stddev_ticks": -0.1}}
            )

    def test_initial_pose_and_vehicle_must_fit_inside_world(self) -> None:
        with self.assertRaisesRegex(ValidationError, "inside the world"):
            CoherentSimulationConfig(
                initial_x_m=2.95,
                world_width_m=6,
                vehicle_radius_m=0.12,
            )

    def test_lidar_rate_must_not_exceed_plant_rate(self) -> None:
        with self.assertRaisesRegex(ValidationError, "must not exceed"):
            CoherentSimulationConfig(
                update_frequency_hz=20,
                lidar_scan_frequency_hz=30,
            )


if __name__ == "__main__":
    unittest.main()
