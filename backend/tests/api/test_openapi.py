import unittest
from typing import Any, Iterator

from fastapi.testclient import TestClient

from app.control_server import app as control_app
from app.main_server import app as main_app
from app.schemas.robot.config import HardwareConfig


JSON_SCHEMA_TYPES = {
    "array",
    "boolean",
    "integer",
    "null",
    "number",
    "object",
    "string",
}


def walk_mappings(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_mappings(child)


class TestOpenAPISchema(unittest.TestCase):
    def test_control_server_openapi_schema_is_valid(self) -> None:
        client = TestClient(control_app)
        response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertIn("/px/api/settings/json-schema", schema["paths"])

        settings_schema_response = client.get("/px/api/settings/json-schema")
        self.assertEqual(settings_schema_response.status_code, 200)

    def test_main_server_openapi_schema_is_valid(self) -> None:
        schema = main_app.openapi()

        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertTrue(schema["paths"])

    def test_ui_widget_metadata_does_not_override_json_schema_type(self) -> None:
        schema = HardwareConfig.model_json_schema()
        custom_widgets = set()

        for mapping in walk_mappings(schema):
            schema_type = mapping.get("type")
            if isinstance(schema_type, str):
                self.assertIn(schema_type, JSON_SCHEMA_TYPES)
            elif isinstance(schema_type, list):
                self.assertTrue(set(schema_type).issubset(JSON_SCHEMA_TYPES))
            widget = mapping.get("x-ui-type")
            if isinstance(widget, str):
                custom_widgets.add(widget)

        self.assertTrue(
            {
                "calibration_offset",
                "hex",
                "motor_direction",
                "pin",
                "select",
                "string_or_number",
            }.issubset(custom_widgets)
        )


if __name__ == "__main__":
    unittest.main()
