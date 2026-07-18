import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from app.core.px_logger import Logger
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.battery import BatteryStatusResponse
from app.schemas.connection import ConnectionEvent
from app.schemas.robot.battery import (
    BatteryConfig,
    INA219BatteryDriverConfig,
    INA226BatteryDriverConfig,
    INA260BatteryDriverConfig,
    SunfounderBatteryConfig,
)
from app.schemas.robot.config import HardwareConfig
from robot_hat import (
    BatteryABC,
    INA219Battery,
    INA226Battery,
    INA260Battery,
    SunfounderBattery,
)

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from robot_hat.i2c.smbus_manager import SMBusManager

_log = Logger(__name__)


class BatteryService:
    def __init__(
        self,
        connection_manager: "ConnectionService",
        config_manager: "JsonDataManager",
        smbus_manager: "SMBusManager",
        app_loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.config_manager = config_manager
        self.connection_manager = connection_manager
        self.config = HardwareConfig(**config_manager.load_data())
        self._smbus_manager = smbus_manager
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._app_loop = app_loop
        self._metrics_cache: Dict[str, Tuple[float, BatteryStatusResponse]] = {}
        self._last_broadcast_time: Dict[str, float] = {}
        self._adapter_errors: Dict[str, str] = {}
        self.battery_adapters: Dict[str, BatteryABC] = {}
        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.on(self.config_manager.LOAD_EVENT, self.update_config)
        self._initialize_adapters()

    @property
    def enabled_batteries(self) -> List[BatteryConfig]:
        return [battery for battery in self.config.batteries if battery.enabled]

    def update_config(self, new_config: Dict[str, Any]) -> None:
        next_config = HardwareConfig(**new_config)
        if self.config.batteries == next_config.batteries:
            self.config = next_config
            return

        if not self._app_loop.is_running():
            self.config = next_config
            self.close_battery_adapters()
            self._reset_runtime_state()
            self._initialize_adapters()
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
                _log.error("Error while updating battery configuration: %s", error)

    async def _apply_config(self, next_config: HardwareConfig) -> None:
        await self._cancel_broadcast_task()
        self.config = next_config
        self.close_battery_adapters()
        self._reset_runtime_state()
        self._initialize_adapters()
        self._start_broadcast_task()

    def _reset_runtime_state(self) -> None:
        self._metrics_cache.clear()
        self._last_broadcast_time.clear()

    def _initialize_adapters(self) -> None:
        self._adapter_errors = {}
        for battery in self.enabled_batteries:
            try:
                adapter = self.make_battery_adapter(
                    battery, bus_manager=self._smbus_manager
                )
                self.battery_adapters[battery.name] = adapter
            except Exception as error:
                message = str(error)
                self._adapter_errors[battery.name] = message
                _log.error("Failed to initialize battery '%s': %s", battery.name, error)

    @staticmethod
    def make_battery_adapter(
        config: BatteryConfig,
        bus_manager: "SMBusManager",
    ) -> BatteryABC:
        driver = config.driver
        bus = bus_manager.get_bus(driver.bus)
        if isinstance(driver, INA219BatteryDriverConfig):
            return INA219Battery(
                address=driver.addr_int,
                config=driver.to_dataclass(),
                bus=bus,
            )
        if isinstance(driver, INA226BatteryDriverConfig):
            return INA226Battery(
                address=driver.addr_int,
                config=driver.to_dataclass(),
                bus=bus,
            )
        if isinstance(driver, INA260BatteryDriverConfig):
            return INA260Battery(
                address=driver.addr_int,
                config=driver.to_dataclass(),
                bus=bus,
            )
        if isinstance(driver, SunfounderBatteryConfig):
            return SunfounderBattery(
                channel=driver.channel, address=driver.addr_int, bus=bus
            )
        raise TypeError(f"Unsupported battery driver: {type(driver).__name__}")

    @staticmethod
    def _read_adapter_metrics(adapter: BatteryABC) -> Tuple[float, Optional[float]]:
        try:
            metrics = adapter.get_battery_metrics()
            return metrics.voltage, metrics.current
        except NotImplementedError:
            return adapter.get_battery_voltage(), None

    async def read_metrics(self, battery: BatteryConfig) -> BatteryStatusResponse:
        cached = self._metrics_cache.get(battery.name)
        if cached and time.monotonic() - cached[0] <= battery.cache_seconds:
            return cached[1]

        adapter = self.battery_adapters.get(battery.name)
        if adapter is None:
            error = self._adapter_errors.get(
                battery.name, "Battery adapter is not initialized"
            )
            return BatteryStatusResponse(
                name=battery.name,
                voltage=None,
                current=None,
                percentage=None,
                error=error,
            )

        async with self._lock:
            cached = self._metrics_cache.get(battery.name)
            if cached and time.monotonic() - cached[0] <= battery.cache_seconds:
                return cached[1]
            try:
                voltage, current = await asyncio.to_thread(
                    self._read_adapter_metrics, adapter
                )
            except Exception as error:
                _log.error("Error reading battery '%s': %s", battery.name, error)
                return BatteryStatusResponse(
                    name=battery.name,
                    voltage=None,
                    current=None,
                    percentage=None,
                    error=str(error),
                )

        status = BatteryStatusResponse(
            name=battery.name,
            voltage=voltage,
            current=current,
            percentage=self._calculate_battery_percentage(battery, voltage),
            error=None,
        )
        self._metrics_cache[battery.name] = (time.monotonic(), status)
        return status

    async def read_all_metrics(
        self, batteries: Optional[Sequence[BatteryConfig]] = None
    ) -> List[BatteryStatusResponse]:
        selected = list(batteries) if batteries is not None else self.enabled_batteries
        return await asyncio.gather(
            *(self.read_metrics(battery) for battery in selected)
        )

    def setup_connection_manager(self) -> None:
        self.connection_manager.on(
            ConnectionEvent.LAST_CONNECTION.value, self._cancel_broadcast_task
        )
        self.connection_manager.on(
            ConnectionEvent.FIRST_ACTIVE_CONNECTION.value, self._start_broadcast_task
        )

    def close_battery_adapters(self) -> None:
        for name, adapter in self.battery_adapters.items():
            try:
                _log.info("Closing battery adapter '%s'", name)
                adapter.close()
            except Exception as error:
                _log.error("Failed to close battery adapter '%s': %s", name, error)
        self.battery_adapters = {}

    async def cleanup_connection_manager(self) -> None:
        self.connection_manager.off(
            ConnectionEvent.FIRST_ACTIVE_CONNECTION.value, self._start_broadcast_task
        )
        self.connection_manager.off(
            ConnectionEvent.LAST_CONNECTION.value, self._cancel_broadcast_task
        )
        await self._cancel_broadcast_task()
        self.close_battery_adapters()

    async def broadcast_state(
        self, batteries: Optional[Sequence[BatteryConfig]] = None
    ) -> List[BatteryStatusResponse]:
        selected = list(batteries) if batteries is not None else self.enabled_batteries
        statuses = await self.read_all_metrics(selected)
        if statuses:
            await self.connection_manager.broadcast_json(
                {
                    "type": "battery",
                    "payload": [status.model_dump(mode="json") for status in statuses],
                }
            )
            now = time.monotonic()
            for battery in selected:
                self._last_broadcast_time[battery.name] = now
        return statuses

    @staticmethod
    def _calculate_battery_percentage(battery: BatteryConfig, voltage: float) -> float:
        adjusted_voltage = max(0.0, voltage - battery.min_voltage)
        voltage_range = battery.full_voltage - battery.min_voltage
        percentage = min(100.0, (adjusted_voltage / voltage_range) * 100)
        return int(percentage * 10) / 10

    def _start_broadcast_task(self) -> None:
        if (
            self._task is None
            and self.enabled_batteries
            and self.connection_manager.active_connections
        ):
            _log.info("Starting battery broadcast loop")
            self._task = asyncio.create_task(self._broadcast_loop())

    async def _cancel_broadcast_task(self) -> None:
        if not self._task:
            return
        _log.info("Cancelling battery task")
        try:
            self._stop_event.set()
            self._task.cancel()
            await self._task
        except asyncio.CancelledError:
            _log.info("Battery task was cancelled")
        finally:
            self._task = None
            self._stop_event.clear()

    async def _broadcast_loop(self) -> None:
        while not self._stop_event.is_set() and self.enabled_batteries:
            now = time.monotonic()
            due = [
                battery
                for battery in self.enabled_batteries
                if now - self._last_broadcast_time.get(battery.name, float("-inf"))
                >= battery.auto_measure_seconds
            ]
            if due:
                statuses = await self.broadcast_state(due)
                for battery, status in zip(due, statuses):
                    self._log_status(battery, status)

            now = time.monotonic()
            delays = [
                max(
                    0.1,
                    battery.auto_measure_seconds
                    - (now - self._last_broadcast_time.get(battery.name, now)),
                )
                for battery in self.enabled_batteries
            ]
            await asyncio.sleep(min(delays, default=1.0))

    @staticmethod
    def _log_status(battery: BatteryConfig, status: BatteryStatusResponse) -> None:
        if status.error or status.voltage is None:
            _log.error("Battery '%s': %s", battery.name, status.error or "read failed")
            return
        message = "Battery '%s': %sV (%s%%), next measurement after %ss"
        args = (
            battery.name,
            status.voltage,
            status.percentage,
            battery.auto_measure_seconds,
        )
        if status.voltage >= battery.warn_voltage:
            _log.info(message, *args)
        elif status.voltage > battery.danger_voltage:
            _log.warning(message, *args)
        elif status.voltage > battery.min_voltage:
            _log.error(message, *args)
        else:
            _log.critical(message, *args)
