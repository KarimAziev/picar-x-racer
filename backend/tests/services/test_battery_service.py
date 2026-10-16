import asyncio
import threading
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.robot.battery import BatteryConfig
from app.schemas.robot.config import HardwareConfig
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
    async def asyncSetUp(self):
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
        self.service.config = HardwareConfig.model_construct(
            batteries=[self.main_config, self.servo_config]
        )
        self.service._metrics_cache = {}
        self.service._adapter_errors = {}
        self.service._lock = asyncio.Lock()
        self.service._lifecycle_lock = asyncio.Lock()
        self.service._closed = False
        self.service._task = None
        self.service._stop_event = asyncio.Event()
        self.service._last_broadcast_time = {}
        self.service._app_loop = asyncio.get_running_loop()
        self.config_manager = MagicMock()
        self.service.config_manager = self.config_manager
        self.service._smbus_manager = MagicMock()
        self.service.battery_adapters = {}
        self.broadcast_json = AsyncMock()
        self.service.connection_manager = MagicMock(broadcast_json=self.broadcast_json)
        self.service.connection_manager.active_connections = []

    async def test_reconfiguration_runs_device_io_off_event_loop(self):
        current_thread = threading.get_ident()
        io_threads: list[int] = []
        config = self.service.config.model_copy(deep=True)
        config.batteries = []

        with patch.object(
            self.service,
            "close_battery_adapters",
            side_effect=lambda: io_threads.append(threading.get_ident()),
        ), patch.object(
            self.service,
            "_initialize_adapters",
            side_effect=lambda: io_threads.append(threading.get_ident()),
        ):
            await self.service._apply_config(config)

        self.assertEqual(len(io_threads), 2)
        self.assertNotIn(current_thread, io_threads)

    async def test_cleanup_waits_for_cancelled_read_without_blocking_loop(self):
        started = threading.Event()
        release = threading.Event()
        adapter = MagicMock()
        self.service.battery_adapters = {self.main_config.name: adapter}

        def blocked_read():
            started.set()
            release.wait(timeout=2)
            return BatteryMetrics(7.2, 0.8)

        adapter.get_battery_metrics.side_effect = blocked_read
        task = asyncio.create_task(self.service.read_metrics(self.main_config))
        self.assertTrue(await asyncio.to_thread(started.wait, 1))
        task.cancel()
        cleanup = asyncio.create_task(self.service.cleanup_connection_manager())
        try:
            await asyncio.sleep(0.01)
            adapter.close.assert_not_called()
            self.assertFalse(cleanup.done())
        finally:
            release.set()
            await asyncio.gather(task, cleanup, return_exceptions=True)

        adapter.close.assert_called_once()

    async def test_shutdown_prevents_adapter_reinitialization(self):
        await self.service.cleanup_connection_manager()
        config = self.service.config.model_copy(deep=True)
        config.batteries = []
        with patch.object(self.service, "_initialize_adapters") as initialize:
            await self.service._apply_config(config)
            self.service.update_config({})
            self.service.connection_manager.active_connections = [MagicMock()]
            self.service._start_broadcast_task()
            initialize.assert_not_called()
        self.assertIsNone(self.service._task)
        self.assertEqual(self.config_manager.off.call_count, 2)

    async def test_cleanup_closes_adapters_after_broadcast_failure(self):
        async def fail():
            raise OSError("Browser disconnected")

        self.service._task = asyncio.create_task(fail())
        await asyncio.sleep(0)
        with patch.object(self.service, "close_battery_adapters") as close:
            await self.service.cleanup_connection_manager()
        close.assert_called_once()
        self.assertIsNone(self.service._task)

    async def test_queued_read_uses_adapter_installed_by_reconfiguration(self):
        previous = MagicMock()
        previous.get_battery_metrics.return_value = BatteryMetrics(7.2, 0.8)
        replacement = MagicMock()
        replacement.get_battery_metrics.return_value = BatteryMetrics(8.0, 0.9)
        self.service.battery_adapters = {self.main_config.name: previous}
        config = self.service.config.model_copy(deep=True)
        config.batteries = [self.main_config]

        with patch.object(
            self.service, "make_battery_adapter", return_value=replacement
        ):
            await self.service._lock.acquire()
            update = asyncio.create_task(self.service._apply_config(config))
            await asyncio.sleep(0)
            read = asyncio.create_task(self.service.read_metrics(self.main_config))
            await asyncio.sleep(0)
            self.service._lock.release()
            await update
            reading = await read

        previous.get_battery_metrics.assert_not_called()
        self.assertEqual(reading.voltage, 8.0)
        self.assertIsNone(reading.error)

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
        self.service.config = HardwareConfig.model_construct(
            batteries=[self.main_config]
        )
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
