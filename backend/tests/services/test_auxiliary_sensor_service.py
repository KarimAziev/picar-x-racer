import asyncio
import unittest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from app.schemas.robot.auxiliary_sensors import (
    HTS221SensorConfig,
    HTS221OutputDataRate,
    MockEnvironmentalSensorConfig,
    MockMagnetometerSensorConfig,
)
from app.services.sensors.auxiliary_sensor_service import AuxiliarySensorService
from robot_hat import HTS221, MockEnvironmentalSensor, MockMagnetometer


class TestAuxiliarySensorService(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.environment_config = MockEnvironmentalSensorConfig(name="Environment")
        self.magnetometer_config = MockMagnetometerSensorConfig(name="Compass")
        self.service = AuxiliarySensorService.__new__(AuxiliarySensorService)
        self.service.config = cast(
            Any,
            SimpleNamespace(
                auxiliary_sensors=SimpleNamespace(
                    sensors=[self.environment_config, self.magnetometer_config]
                )
            ),
        )
        environment = MockEnvironmentalSensor(monotonic_ns=lambda: 10)
        magnetometer = MockMagnetometer(monotonic_ns=lambda: 11)
        environment.initialize()
        magnetometer.initialize()
        self.service._adapters = {
            "Environment": environment,
            "Compass": magnetometer,
        }
        self.service._adapter_errors = {}
        self.service._cache = {}
        self.service._last_broadcast_time = {}
        self.service._lock = asyncio.Lock()
        self.broadcast_json = AsyncMock()
        self.service.connection_manager = MagicMock(broadcast_json=self.broadcast_json)

    async def test_reads_typed_environmental_and_magnetic_payloads(self) -> None:
        readings = await self.service.read_all()

        self.assertEqual(readings[0].kind, "environmental")
        self.assertEqual(readings[0].pressure_pa, 101_325.0)
        self.assertEqual(readings[1].kind, "magnetometer")
        self.assertEqual(readings[1].magnetic_field_t, (20e-6, 0.0, 45e-6))

    async def test_caches_and_broadcasts_named_list(self) -> None:
        first = await self.service.read_sensor(self.environment_config)
        second = await self.service.read_sensor(self.environment_config)
        self.assertIs(first, second)

        readings = await self.service.broadcast_state()

        self.assertEqual(len(readings), 2)
        message = self.broadcast_json.call_args.args[0]
        self.assertEqual(message["type"], "auxiliary_sensors")
        self.assertEqual(message["payload"][0]["name"], "Environment")

    async def test_isolates_read_and_initialization_errors(self) -> None:
        adapter = cast(MockEnvironmentalSensor, self.service._adapters["Environment"])
        adapter.set_available(False)
        reading = await self.service.read_sensor(self.environment_config)
        self.assertIn("unavailable", reading.error or "")

        self.service._adapters = {}
        self.service._adapter_errors = {"Environment": "not connected"}
        self.service._cache = {}
        reading = await self.service.read_sensor(self.environment_config)
        self.assertEqual(reading.error, "not connected")

    def test_factory_injects_shared_bus_and_typed_driver_config(self) -> None:
        bus_manager = MagicMock()
        bus = MagicMock()
        bus_manager.get_bus.return_value = bus
        config = HTS221SensorConfig(
            output_data_rate_hz=HTS221OutputDataRate.HZ_7,
            poll_interval_seconds=1,
            humidity_average_samples=128,
            temperature_average_samples=64,
        )

        adapter = AuxiliarySensorService.make_adapter(config, bus_manager)

        assert isinstance(adapter, HTS221)
        self.assertIs(adapter.bus, bus)
        self.assertFalse(adapter.own_bus)
        self.assertEqual(adapter.config.output_data_rate_hz, 7.0)
        self.assertEqual(adapter.config.humidity_average_samples, 128)


if __name__ == "__main__":
    unittest.main()
