import asyncio
import unittest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from app.schemas.robot.battery import BatteryConfig
from app.services.sensors.battery_service import BatteryService
from robot_hat.data_types import BatteryMetrics


class TestBatteryAdapterMetrics(unittest.TestCase):
    def test_reads_voltage_and_current_metrics(self):
        adapter = MagicMock()
        adapter.get_battery_metrics.return_value = BatteryMetrics(8.1, 1.25)

        result = BatteryService._read_adapter_metrics(adapter)

        self.assertEqual(result, (8.1, 1.25))
        adapter.get_battery_voltage.assert_not_called()

    def test_falls_back_to_voltage_for_unsupported_current(self):
        adapter = MagicMock()
        adapter.get_battery_metrics.side_effect = NotImplementedError
        adapter.get_battery_voltage.return_value = 7.9

        result = BatteryService._read_adapter_metrics(adapter)

        self.assertEqual(result, (7.9, None))
        adapter.get_battery_voltage.assert_called_once_with()

    def test_does_not_hide_other_metric_errors(self):
        adapter = MagicMock()
        adapter.get_battery_metrics.side_effect = OSError("I2C failure")

        with self.assertRaisesRegex(OSError, "I2C failure"):
            BatteryService._read_adapter_metrics(adapter)


class TestBatteryService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.main_config = BatteryConfig(
            name="Main battery",
            enabled=True,
            min_voltage=6.0,
            danger_voltage=6.5,
            warn_voltage=7.15,
            full_voltage=8.4,
            cache_seconds=2,
        )
        self.servo_config = BatteryConfig(
            name="Servo supply",
            enabled=True,
            min_voltage=4.0,
            danger_voltage=4.5,
            warn_voltage=5.0,
            full_voltage=6.0,
            cache_seconds=2,
        )
        self.service = BatteryService.__new__(BatteryService)
        self.service.config = cast(
            Any,
            SimpleNamespace(batteries=[self.main_config, self.servo_config]),
        )
        self.service._metrics_cache = {}
        self.service._adapter_errors = {}
        self.service._lock = asyncio.Lock()
        self.broadcast_json = AsyncMock()
        self.service.connection_manager = MagicMock(broadcast_json=self.broadcast_json)

    async def test_reads_and_caches_metrics(self):
        adapter = MagicMock()
        adapter.get_battery_metrics.return_value = BatteryMetrics(7.2, 0.8)
        self.service.battery_adapters = {self.main_config.name: adapter}

        first = await self.service.read_metrics(self.main_config)
        second = await self.service.read_metrics(self.main_config)

        self.assertEqual(first.current, 0.8)
        self.assertEqual(first.percentage, 50.0)
        self.assertIs(first, second)
        adapter.get_battery_metrics.assert_called_once_with()

    async def test_isolates_sensor_failures(self):
        main_adapter = MagicMock()
        main_adapter.get_battery_metrics.return_value = BatteryMetrics(8.0, 1.1)
        servo_adapter = MagicMock()
        servo_adapter.get_battery_metrics.side_effect = OSError("Servo sensor failed")
        self.service.battery_adapters = {
            self.main_config.name: main_adapter,
            self.servo_config.name: servo_adapter,
        }

        statuses = await self.service.read_all_metrics()

        self.assertEqual(statuses[0].voltage, 8.0)
        self.assertIsNone(statuses[0].error)
        self.assertIsNone(statuses[1].voltage)
        self.assertEqual(statuses[1].error, "Servo sensor failed")

    async def test_broadcasts_list_payload(self):
        adapter = MagicMock()
        adapter.get_battery_metrics.return_value = BatteryMetrics(8.4, 0.5)
        self.service.battery_adapters = {self.main_config.name: adapter}
        self.service.config = cast(Any, SimpleNamespace(batteries=[self.main_config]))
        self.service._last_broadcast_time = {}

        statuses = await self.service.broadcast_state()

        self.assertEqual(len(statuses), 1)
        payload = self.broadcast_json.call_args.args[0]
        self.assertEqual(payload["type"], "battery")
        self.assertEqual(payload["payload"][0]["name"], "Main battery")
        self.assertEqual(payload["payload"][0]["current"], 0.5)

    def test_clamps_percentage_to_supported_range(self):
        self.assertEqual(
            BatteryService._calculate_battery_percentage(self.main_config, 20), 100.0
        )
        self.assertEqual(
            BatteryService._calculate_battery_percentage(self.main_config, 2), 0.0
        )


if __name__ == "__main__":
    unittest.main()
