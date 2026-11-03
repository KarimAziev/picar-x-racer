"""UI metadata and actionable validation for robot setup."""

import unittest

from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.mapping import LocalMappingConfig
from app.util.settings_errors import format_settings_errors
from pydantic import ValidationError


class TestSettingsHelp(unittest.TestCase):
    def test_physical_quantity_labels_include_units(self) -> None:
        units = {
            "_m_per_meter": "m/m",
            "_rad_per_second": "rad/s",
            "_seconds": "s",
            "_mps2": "m/s²",
            "_radps": "rad/s",
            "_mps": "m/s",
            "_dps": "degrees/s",
            "_rps": "rev/s",
            "_ms": "ms",
            "_cm": "cm",
            "_deg": "degrees",
            "_rad": "rad",
            "_hz": "Hz",
            "_m": "m",
            "_s": "s",
        }
        schema = HardwareConfig.model_json_schema()
        for model, definition in schema["$defs"].items():
            for name, field in definition.get("properties", {}).items():
                unit = next(
                    (unit for suffix, unit in units.items() if name.endswith(suffix)),
                    None,
                )
                if unit:
                    with self.subTest(model=model, field=name):
                        self.assertIn(f"({unit})", field.get("title", ""))

    def test_time_fields_without_unit_suffixes_have_units(self) -> None:
        definitions = HardwareConfig.model_json_schema()["$defs"]
        for model, name, unit in (
            ("UltrasonicConfig", "timeout", "s"),
            ("LedConfig", "interval", "s"),
            ("AngularServoConfig", "min_pulse", "µs"),
            ("AngularServoConfig", "max_pulse", "µs"),
            ("INA260Config", "voltage_conversion_time", "µs"),
            ("INA226Config", "bus_conv_time", "µs"),
        ):
            with self.subTest(model=model, field=name):
                self.assertIn(unit, definitions[model]["properties"][name]["title"])

    def test_validation_uses_form_labels_without_debug_details(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            LocalMappingConfig(width_m=0)
        message = format_settings_errors(
            caught.exception, LocalMappingConfig.model_json_schema()
        )
        self.assertIn("Map width (m):", message)
        self.assertIn("greater than 1", message)
        for technical_detail in ("input_value", "pydantic.dev", "type=", "width_m"):
            self.assertNotIn(technical_detail, message)

    def test_labels_are_resolved_within_their_settings_section(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            HardwareConfig.model_validate({"motion_control": {"command_timeout_ms": 1}})
        message = format_settings_errors(
            caught.exception, HardwareConfig.model_json_schema()
        )
        self.assertIn("Motion control > Command timeout (ms)", message)
        self.assertNotIn("Simulation command timeout", message)
