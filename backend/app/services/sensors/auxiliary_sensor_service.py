"""Acquisition and browser telemetry for non-localization sensors."""

import asyncio
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple, Union

from app.core.px_logger import Logger
from app.schemas.auxiliary_sensors import AuxiliarySensorReading
from app.schemas.connection import ConnectionEvent
from app.schemas.robot.auxiliary_sensors import (
    AuxiliarySensorConfig,
    HTS221SensorConfig,
    LIS3MDLSensorConfig,
    LPS25HSensorConfig,
    LSM9DS1MagnetometerSensorConfig,
    MockEnvironmentalSensorConfig,
    MockMagnetometerSensorConfig,
)
from app.schemas.robot.config import HardwareConfig
from app.util.async_threads import run_in_thread
from robot_hat import (
    EnvironmentalSensorABC,
    HTS221,
    HTS221Config,
    LIS3MDL,
    LIS3MDLConfig,
    LPS25H,
    LPS25HConfig,
    LSM9DS1Magnetometer,
    LSM9DS1MagnetometerConfig,
    MagnetometerABC,
    MockEnvironmentalSensor,
    MockMagnetometer,
)

if TYPE_CHECKING:
    from app.managers.file_management.json_data_manager import JsonDataManager
    from app.services.connection_service import ConnectionService
    from robot_hat.i2c.smbus_manager import SMBusManager


_log = Logger(__name__)
AuxiliarySensorAdapter = Union[EnvironmentalSensorABC, MagnetometerABC]


class AuxiliarySensorService:
    """Own configured sensor adapters and publish independent telemetry."""

    def __init__(
        self,
        connection_manager: "ConnectionService",
        config_manager: "JsonDataManager",
        smbus_manager: "SMBusManager",
        app_loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.connection_manager = connection_manager
        self.config_manager = config_manager
        self.config = HardwareConfig.model_validate(config_manager.load_data())
        self._smbus_manager = smbus_manager
        self._app_loop = app_loop
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()
        self._lifecycle_lock = asyncio.Lock()
        self._closed = False
        self._adapters: Dict[str, AuxiliarySensorAdapter] = {}
        self._adapter_errors: Dict[str, str] = {}
        self._cache: Dict[str, Tuple[float, AuxiliarySensorReading]] = {}
        self._last_broadcast_time: Dict[str, float] = {}
        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.on(self.config_manager.LOAD_EVENT, self.update_config)
        self._initialize_adapters()

    @property
    def enabled_sensors(self) -> List[AuxiliarySensorConfig]:
        return [
            sensor for sensor in self.config.auxiliary_sensors.sensors if sensor.enabled
        ]

    @property
    def adapters(self) -> Dict[str, AuxiliarySensorAdapter]:
        return dict(self._adapters)

    def update_config(self, new_config: Dict[str, object]) -> None:
        if self._closed:
            return
        next_config = HardwareConfig.model_validate(new_config)
        if not self._app_loop.is_running():
            if self.config.auxiliary_sensors == next_config.auxiliary_sensors:
                self.config = next_config
            else:
                self._replace_adapters(next_config)
            return
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is self._app_loop:
            self._app_loop.create_task(self._apply_config(next_config))
        else:
            future = asyncio.run_coroutine_threadsafe(
                self._apply_config(next_config), self._app_loop
            )
            try:
                future.result(timeout=5)
            except Exception as error:
                _log.error(
                    "Error while updating auxiliary sensor configuration: %s", error
                )

    async def _apply_config(self, next_config: HardwareConfig) -> None:
        async with self._lifecycle_lock:
            if self._closed:
                return
            if self.config.auxiliary_sensors == next_config.auxiliary_sensors:
                self.config = next_config
                return
            await self._cancel_broadcast_task()
            async with self._lock:
                if self._closed:
                    return
                await run_in_thread(self._replace_adapters, next_config)
            if not self.enabled_sensors and self.connection_manager.active_connections:
                await self.broadcast_state()
            self._start_broadcast_task()

    def _replace_adapters(self, next_config: HardwareConfig) -> None:
        self.config = next_config
        self.close_adapters()
        self._reset_runtime_state()
        self._initialize_adapters()

    def _initialize_adapters(self) -> None:
        self._adapter_errors = {}
        for sensor in self.enabled_sensors:
            adapter: Optional[AuxiliarySensorAdapter] = None
            try:
                adapter = self.make_adapter(sensor, self._smbus_manager)
                adapter.initialize()
                self._adapters[sensor.name] = adapter
            except Exception as error:
                if adapter is not None:
                    try:
                        adapter.close()
                    except Exception as close_error:
                        _log.error(
                            "Failed to close partially initialized sensor '%s': %s",
                            sensor.name,
                            close_error,
                        )
                self._adapter_errors[sensor.name] = str(error)
                _log.error(
                    "Failed to initialize auxiliary sensor '%s': %s", sensor.name, error
                )

    @staticmethod
    def make_adapter(
        config: AuxiliarySensorConfig, bus_manager: "SMBusManager"
    ) -> AuxiliarySensorAdapter:
        if isinstance(config, HTS221SensorConfig):
            return HTS221(
                address=config.address_int,
                bus=bus_manager.get_bus(config.bus),
                config=HTS221Config(
                    output_data_rate_hz=config.output_data_rate_hz.value,
                    humidity_average_samples=config.humidity_average_samples,
                    temperature_average_samples=config.temperature_average_samples,
                ),
            )
        if isinstance(config, LPS25HSensorConfig):
            return LPS25H(
                address=config.address_int,
                bus=bus_manager.get_bus(config.bus),
                config=LPS25HConfig(
                    output_data_rate_hz=config.output_data_rate_hz.value
                ),
            )
        if isinstance(config, LIS3MDLSensorConfig):
            return LIS3MDL(
                address=config.address_int,
                bus=bus_manager.get_bus(config.bus),
                config=LIS3MDLConfig(
                    magnetic_field_range_gauss=config.magnetic_field_range_gauss,
                    output_data_rate_hz=config.output_data_rate_hz.value,
                    performance_mode=config.performance_mode,
                ),
            )
        if isinstance(config, LSM9DS1MagnetometerSensorConfig):
            return LSM9DS1Magnetometer(
                address=config.address_int,
                bus=bus_manager.get_bus(config.bus),
                config=LSM9DS1MagnetometerConfig(
                    magnetic_field_range_gauss=config.magnetic_field_range_gauss,
                    output_data_rate_hz=config.output_data_rate_hz.value,
                    performance_mode=config.performance_mode,
                ),
            )
        if isinstance(config, MockEnvironmentalSensorConfig):
            return MockEnvironmentalSensor(
                temperature_c=config.temperature_c,
                relative_humidity_percent=config.relative_humidity_percent,
                pressure_pa=config.pressure_pa,
            )
        if isinstance(config, MockMagnetometerSensorConfig):
            return MockMagnetometer(magnetic_field_t=config.magnetic_field_t)
        raise TypeError(f"unsupported auxiliary sensor config: {type(config)!r}")

    async def read_sensor(
        self, config: AuxiliarySensorConfig
    ) -> AuxiliarySensorReading:
        async with self._lock:
            if self._closed:
                return self._error_reading(config, "Sensor service is shut down")
            cached = self._cache.get(config.name)
            if cached and time.monotonic() - cached[0] < config.poll_interval_seconds:
                return cached[1]
            adapter = self._adapters.get(config.name)
            if adapter is None:
                return self._error_reading(
                    config,
                    self._adapter_errors.get(
                        config.name, "sensor adapter is not initialized"
                    ),
                )
            try:
                if isinstance(adapter, EnvironmentalSensorABC):
                    sample = await run_in_thread(adapter.read_sample)
                    reading = AuxiliarySensorReading(
                        name=config.name,
                        driver=config.driver,
                        kind="environmental",
                        timestamp_monotonic_ns=sample.timestamp_monotonic_ns,
                        temperature_c=sample.temperature_c,
                        relative_humidity_percent=sample.relative_humidity_percent,
                        pressure_pa=sample.pressure_pa,
                    )
                else:
                    sample = await run_in_thread(adapter.read_sample)
                    reading = AuxiliarySensorReading(
                        name=config.name,
                        driver=config.driver,
                        kind="magnetometer",
                        timestamp_monotonic_ns=sample.timestamp_monotonic_ns,
                        magnetic_field_t=sample.magnetic_field_t,
                    )
            except Exception as error:
                _log.error(
                    "Error reading auxiliary sensor '%s': %s", config.name, error
                )
                reading = self._error_reading(config, str(error))
            self._cache[config.name] = (time.monotonic(), reading)
            return reading

    async def read_all(
        self, sensors: Optional[Sequence[AuxiliarySensorConfig]] = None
    ) -> List[AuxiliarySensorReading]:
        selected = list(sensors) if sensors is not None else self.enabled_sensors
        return await asyncio.gather(*(self.read_sensor(sensor) for sensor in selected))

    async def broadcast_state(
        self, sensors: Optional[Sequence[AuxiliarySensorConfig]] = None
    ) -> List[AuxiliarySensorReading]:
        due = list(sensors) if sensors is not None else self.enabled_sensors
        await self.read_all(due)
        # Every payload is a complete snapshot. Devices whose individual poll
        # interval is not due return their cached reading from read_sensor().
        readings = await self.read_all()
        await self.connection_manager.broadcast_json(
            {
                "type": "auxiliary_sensors",
                "payload": [reading.model_dump(mode="json") for reading in readings],
            }
        )
        now = time.monotonic()
        for sensor in due:
            self._last_broadcast_time[sensor.name] = now
        return readings

    def setup_connection_manager(self) -> None:
        self.connection_manager.on(
            ConnectionEvent.FIRST_ACTIVE_CONNECTION.value,
            self._start_broadcast_task,
        )
        self.connection_manager.on(
            ConnectionEvent.LAST_CONNECTION.value,
            self._cancel_broadcast_task,
        )

    async def cleanup_connection_manager(self) -> None:
        self._closed = True
        self.config_manager.off(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.off(self.config_manager.LOAD_EVENT, self.update_config)
        self.connection_manager.off(
            ConnectionEvent.FIRST_ACTIVE_CONNECTION.value,
            self._start_broadcast_task,
        )
        self.connection_manager.off(
            ConnectionEvent.LAST_CONNECTION.value,
            self._cancel_broadcast_task,
        )
        async with self._lifecycle_lock:
            await self._cancel_broadcast_task()
            async with self._lock:
                await run_in_thread(self.close_adapters)
                self._reset_runtime_state()

    def close_adapters(self) -> None:
        for name, adapter in self._adapters.items():
            try:
                adapter.close()
            except Exception as error:
                _log.error("Failed to close auxiliary sensor '%s': %s", name, error)
        self._adapters = {}

    def _reset_runtime_state(self) -> None:
        self._cache.clear()
        self._last_broadcast_time.clear()

    def _start_broadcast_task(self) -> None:
        if (
            not self._closed
            and self._task is None
            and self.enabled_sensors
            and self.connection_manager.active_connections
        ):
            self._task = asyncio.create_task(self._broadcast_loop())

    async def _cancel_broadcast_task(self) -> None:
        if self._task is None:
            return
        try:
            self._stop_event.set()
            self._task.cancel()
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception as error:
            _log.error("Auxiliary sensor broadcast task failed: %s", error)
        finally:
            self._task = None
            self._stop_event.clear()

    async def _broadcast_loop(self) -> None:
        while not self._stop_event.is_set() and self.enabled_sensors:
            now = time.monotonic()
            due = [
                sensor
                for sensor in self.enabled_sensors
                if now - self._last_broadcast_time.get(sensor.name, float("-inf"))
                >= sensor.poll_interval_seconds
            ]
            if due:
                await self.broadcast_state(due)
            now = time.monotonic()
            delays = [
                max(
                    0.05,
                    sensor.poll_interval_seconds
                    - (now - self._last_broadcast_time.get(sensor.name, now)),
                )
                for sensor in self.enabled_sensors
            ]
            await asyncio.sleep(min(delays, default=1.0))

    @staticmethod
    def _error_reading(
        config: AuxiliarySensorConfig, error: str
    ) -> AuxiliarySensorReading:
        kind = (
            "magnetometer"
            if isinstance(
                config,
                (
                    LIS3MDLSensorConfig,
                    LSM9DS1MagnetometerSensorConfig,
                    MockMagnetometerSensorConfig,
                ),
            )
            else "environmental"
        )
        return AuxiliarySensorReading(
            name=config.name,
            driver=config.driver,
            kind=kind,
            error=error,
        )


__all__ = ["AuxiliarySensorService"]
