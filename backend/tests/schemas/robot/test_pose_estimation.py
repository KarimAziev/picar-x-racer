import json
import unittest
from copy import deepcopy
from pathlib import Path

from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.pose_estimation import (
    PoseEstimationConfig,
    SimulationScanMatchingConfig,
)
from pydantic import ValidationError


class TestPoseEstimationConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        cls.root_data = json.loads(root_config.read_text())

    def test_missing_block_keeps_existing_configuration_valid(self) -> None:
        data = deepcopy(self.root_data)
        data.pop("pose_estimation", None)

        config = HardwareConfig.model_validate(data)

        self.assertFalse(config.pose_estimation.enabled)
        self.assertEqual(config.pose_estimation.imu_yaw_rate_weight, 0.35)

    def test_enabled_pose_estimation_requires_odometry(self) -> None:
        data = deepcopy(self.root_data)
        data["pose_estimation"]["enabled"] = True

        with self.assertRaisesRegex(ValidationError, "requires Ackermann odometry"):
            HardwareConfig.model_validate(data)

    def test_validates_blend_weight_and_noise(self) -> None:
        with self.assertRaises(ValidationError):
            PoseEstimationConfig(imu_yaw_rate_weight=1.1)
        with self.assertRaises(ValidationError):
            PoseEstimationConfig(position_process_noise_m_per_meter=-0.1)

    def test_scan_matching_defaults_are_backward_compatible_and_disabled(self) -> None:
        config = PoseEstimationConfig()

        self.assertFalse(config.simulation_scan_matching.enabled)
        self.assertEqual(config.simulation_scan_matching.max_scan_points, 48)

    def test_scan_matching_validates_search_resolution(self) -> None:
        with self.assertRaisesRegex(ValidationError, "refinement"):
            SimulationScanMatchingConfig(
                coarse_translation_step_m=0.01,
                refinement_translation_step_m=0.02,
            )

    def test_enabled_scan_matching_requires_full_simulation_stack(self) -> None:
        data = deepcopy(self.root_data)
        data["pose_estimation"]["simulation_scan_matching"] = {"enabled": True}

        with self.assertRaisesRegex(ValidationError, "requires pose estimation"):
            HardwareConfig.model_validate(data)


if __name__ == "__main__":
    unittest.main()
