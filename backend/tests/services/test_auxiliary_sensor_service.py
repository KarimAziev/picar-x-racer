import asyncio
import threading
import unittest
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.robot.auxiliary_sensors import (
    HTS221SensorConfig,
    HTS221OutputDataRate,
    LIS3MDLOutputDataRate,
    LIS3MDLSensorConfig,
    MockEnvironmentalSensorConfig,
    MockMagnetometerSensorConfig,
    AuxiliarySensorsConfig,
)
from app.schemas.robot.config import HardwareConfig
from app.services.sensors.auxiliary_sensor_service import AuxiliarySensorService
from robot_hat import (
    HTS221,
    LIS3MDL,
    LIS3MDLConfig,
    MockEnvironmentalSensor,
    MockMagnetometer,
    SMBusABC,
)
from robot_hat.i2c.smbus_manager import SMBusManager


class TestAuxiliarySensorService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.environment_config = MockEnvironmentalSensorConfig(name="Environment")
        self.magnetometer_config = MockMagnetometerSensorConfig(name="Compass")
        self.service = AuxiliarySensorService.__new__(AuxiliarySensorService)
        self.service.config = HardwareConfig.model_construct(
            auxiliary_sensors=AuxiliarySensorsConfig(
                sensors=[self.environment_config, self.magnetometer_config]
            )
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
        self.service._lifecycle_lock = asyncio.Lock()
        self.service._stop_event = asyncio.Event()
        self.service._task = None
        self.service._closed = False
        self.service._app_loop = asyncio.get_running_loop()
        self.config_manager = MagicMock()
        self.service.config_manager = self.config_manager
        self.service._smbus_manager = MagicMock()
        self.broadcast_json = AsyncMock()
        self.service.connection_manager = MagicMock(broadcast_json=self.broadcast_json)
        self.service.connection_manager.active_connections = []

    async def test_reconfiguration_runs_device_io_off_event_loop(self) -> None:
        current_thread = threading.get_ident()
        close_threads: list[int] = []
        init_threads: list[int] = []
        config = self.service.config.model_copy(deep=True)
        config.auxiliary_sensors.sensors = []

        with patch.object(
            self.service,
            "close_adapters",
            side_effect=lambda: close_threads.append(threading.get_ident()),
        ), patch.object(
            self.service,
            "_initialize_adapters",
            side_effect=lambda: init_threads.append(threading.get_ident()),
        ):
            await self.service._apply_config(config)

        self.assertEqual(len(close_threads), 1)
        self.assertEqual(len(init_threads), 1)
        self.assertNotIn(current_thread, close_threads + init_threads)

    async def test_cleanup_waits_for_cancelled_read_without_blocking_loop(self) -> None:
        adapter = self.service._adapters["Environment"]
        original_read = adapter.read_sample
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()

        def blocked_read():
            started.set()
            release.wait(timeout=2)
            try:
                return original_read()
            finally:
                finished.set()

        with patch.object(
            adapter, "read_sample", side_effect=blocked_read
        ), patch.object(adapter, "close", wraps=adapter.close) as close:
            task = asyncio.create_task(
                self.service.read_sensor(self.environment_config)
            )
            self.assertTrue(await asyncio.to_thread(started.wait, 1))
            task.cancel()
            cleanup = asyncio.create_task(self.service.cleanup_connection_manager())
            try:
                await asyncio.sleep(0.01)
                close.assert_not_called()
                self.assertFalse(cleanup.done())
            finally:
                release.set()
                await asyncio.gather(task, cleanup, return_exceptions=True)

            self.assertTrue(finished.is_set())
            close.assert_called_once()

    async def test_shutdown_prevents_adapter_reinitialization(self) -> None:
        await self.service.cleanup_connection_manager()
        config = self.service.config.model_copy(deep=True)
        config.auxiliary_sensors.sensors = []
        with patch.object(self.service, "_initialize_adapters") as initialize:
            await self.service._apply_config(config)
            self.service.update_config({})
            self.service.connection_manager.active_connections = [MagicMock()]
            self.service._start_broadcast_task()
            initialize.assert_not_called()
        self.assertIsNone(self.service._task)
        self.assertEqual(self.config_manager.off.call_count, 2)

    async def test_cleanup_closes_adapters_after_broadcast_failure(self) -> None:
        async def fail():
            raise OSError("Browser disconnected")

        self.service._task = asyncio.create_task(fail())
        await asyncio.sleep(0)
        with patch.object(self.service, "close_adapters") as close:
            await self.service.cleanup_connection_manager()
        close.assert_called_once()
        self.assertIsNone(self.service._task)

    async def test_queued_read_uses_adapter_installed_by_reconfiguration(self) -> None:
        previous = self.service._adapters["Environment"]
        replacement = MockEnvironmentalSensor(temperature_c=35.0)
        config = self.service.config.model_copy(deep=True)
        config.auxiliary_sensors.sensors = [
            self.environment_config.model_copy(update={"temperature_c": 35.0})
        ]

        with patch.object(
            self.service, "make_adapter", return_value=replacement
        ), patch.object(
            previous, "read_sample", wraps=previous.read_sample
        ) as old_read:
            await self.service._lock.acquire()
            update = asyncio.create_task(self.service._apply_config(config))
            await asyncio.sleep(0)
            read = asyncio.create_task(
                self.service.read_sensor(self.environment_config)
            )
            await asyncio.sleep(0)
            self.service._lock.release()
            await update
            reading = await read

        old_read.assert_not_called()
        self.assertEqual(reading.temperature_c, 35.0)
        self.assertIsNone(reading.error)

    async def test_overlapping_configuration_updates_initialize_in_order(self) -> None:
        started = threading.Event()
        release = threading.Event()
        names: list[str] = []
        first = self.service.config.model_copy(deep=True)
        first.auxiliary_sensors.sensors = [MockEnvironmentalSensorConfig(name="First")]
        second = self.service.config.model_copy(deep=True)
        second.auxiliary_sensors.sensors = [
            MockEnvironmentalSensorConfig(name="Second")
        ]

        def initialize():
            names.append(self.service.enabled_sensors[0].name)
            if len(names) == 1:
                started.set()
                release.wait(timeout=2)

        with patch.object(self.service, "_initialize_adapters", side_effect=initialize):
            first_update = asyncio.create_task(self.service._apply_config(first))
            self.assertTrue(await asyncio.to_thread(started.wait, 1))
            second_update = asyncio.create_task(self.service._apply_config(second))
            try:
                await asyncio.sleep(0.01)
                self.assertEqual(names, ["First"])
                self.assertFalse(second_update.done())
            finally:
                release.set()
                await asyncio.gather(first_update, second_update)

        self.assertEqual(names, ["First", "Second"])
        self.assertEqual(self.service.config, second)

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

    def test_lis3mdl_factory_preserves_config_and_shared_bus_ownership(self) -> None:
        bus_manager = MagicMock(spec=SMBusManager)
        bus = MagicMock(spec=SMBusABC)
        bus_manager.get_bus.return_value = bus
        config = LIS3MDLSensorConfig(
            bus=2,
            address="0x1c",
            magnetic_field_range_gauss=12,
            output_data_rate_hz=LIS3MDLOutputDataRate.HZ_40,
            performance_mode="high",
        )

        adapter = AuxiliarySensorService.make_adapter(config, bus_manager)

        assert isinstance(adapter, LIS3MDL)
        bus_manager.get_bus.assert_called_once_with(2)
        self.assertIs(adapter.bus, bus)
        self.assertFalse(adapter.own_bus)
        self.assertEqual(adapter.address, 0x1C)
        self.assertEqual(
            adapter.config,
            LIS3MDLConfig(
                magnetic_field_range_gauss=12,
                output_data_rate_hz=40.0,
                performance_mode="high",
            ),
        )
        self.service._adapters = {config.name: adapter}
        self.service.close_adapters()
        bus.close.assert_not_called()
        self.assertEqual(self.service.adapters, {})

    async def test_lis3mdl_publishes_native_magnetic_vector_and_timestamp(self) -> None:
        config = LIS3MDLSensorConfig(name="MiniIMU compass")
        adapter = MockMagnetometer(
            magnetic_field_t=(12e-6, -34e-6, 56e-6), monotonic_ns=lambda: 123
        )
        adapter.initialize()
        self.service._adapters = {config.name: adapter}

        reading = await self.service.read_sensor(config)

        self.assertEqual(reading.name, "MiniIMU compass")
        self.assertEqual(reading.driver, "lis3mdl")
        self.assertEqual(reading.kind, "magnetometer")
        self.assertEqual(reading.magnetic_field_t, (12e-6, -34e-6, 56e-6))
        self.assertEqual(reading.timestamp_monotonic_ns, 123)
        self.assertIsNone(reading.temperature_c)
        self.assertIsNone(reading.error)

    async def test_lis3mdl_read_and_initialization_errors_remain_magnetic(self) -> None:
        config = LIS3MDLSensorConfig()
        adapter = MockMagnetometer()
        adapter.initialize()
        adapter.set_available(False)
        self.service._adapters = {config.name: adapter}

        reading = await self.service.read_sensor(config)

        self.assertEqual(reading.driver, "lis3mdl")
        self.assertEqual(reading.kind, "magnetometer")
        self.assertIsNone(reading.magnetic_field_t)
        self.assertIn("unavailable", reading.error or "")

        self.service._adapters = {}
        self.service._cache = {}
        self.service._adapter_errors = {config.name: "LIS3MDL WHO_AM_I mismatch"}

        reading = await self.service.read_sensor(config)

        self.assertEqual(reading.driver, "lis3mdl")
        self.assertEqual(reading.kind, "magnetometer")
        self.assertIsNone(reading.magnetic_field_t)
        self.assertEqual(reading.error, "LIS3MDL WHO_AM_I mismatch")


if __name__ == "__main__":
    unittest.main()
