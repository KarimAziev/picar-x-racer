import math
import unittest
from pydantic import ValidationError
from app.schemas.robot.navigation import NavigationConfig


class NavigationConfigTests(unittest.TestCase):
    def test_body_envelope_uses_rear_axle_not_body_center(self) -> None:
        config = NavigationConfig(
            use_body_clearance=True,
            body_length_m=0.57,
            body_width_m=0.3,
            rear_overhang_m=0.1,
        )
        self.assertAlmostEqual(config.body_radius_m, math.hypot(0.47, 0.15))
        self.assertTrue(config.prefer_forward)

    def test_measurements_do_not_enable_envelope_implicitly(self) -> None:
        self.assertEqual(NavigationConfig(body_length_m=0.57).body_radius_m, 0)

    def test_incomplete_or_invalid_enabled_envelope_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            NavigationConfig(use_body_clearance=True, body_length_m=0.57)
        with self.assertRaises(ValidationError):
            NavigationConfig(body_length_m=0.57, rear_overhang_m=0.57)
        with self.assertRaises(ValidationError):
            NavigationConfig(body_length_m=float("nan"))
