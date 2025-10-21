import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

from app.core.px_logger import Logger
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.connection import ConnectionEvent
from app.schemas.robot.battery import (
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
        """
        Initializes the BatteryService with required file and connection services.
        """

        self.config_manager = config_manager
        self.connection_manager = connection_manager
        self.config = HardwareConfig(**config_manager.load_data())
        self._smbus_manager = smbus_manager
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_measure_voltage: Optional[float] = None
        self._last_measure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        self._app_loop = app_loop
        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.on(self.config_manager.LOAD_EVENT, self.update_config)
        self.battery_adapter: Optional[BatteryABC] = None
        try:
            self.battery_adapter = self.make_battery_adapter(
                self.config, bus_manager=self._smbus_manager
            )
        except Exception as e:
            _log.error("Failed to init battery adapter: %s ", e)

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Updates the robot configuration.

        If the distance process is running, it will be stopped and restarted with the new
        configuration.

        Args:
            new_config: The dictionary with new robot config.
        """
        old_config_dict = (
            self.config.battery.model_dump() if self.config.battery else None
        )
        self.config = HardwareConfig(**new_config)

        next_battery_config = (
            self.config.battery.model_dump() if self.config.battery else None
        )
        _log.info(
            "Updating battery config",
        )

        should_close_adapter = False
        should_cancel_task = False
        disabled = not self.config.battery or not self.config.battery.enabled

        if old_config_dict and next_battery_config:
            for key, value in old_config_dict.items():
                next_value = next_battery_config.get(key)
                _log.info(
                    "KEY=%s, OLD_VALUE=%s",
                    key,
                    value,
                )
                _log.info(
                    "KEY=%s, NEXT_VALUE= %s",
                    key,
                    next_value,
                )
                if key == "driver":
                    should_close_adapter = next_value != value
                else:
                    should_cancel_task = (
                        should_cancel_task or value != next_battery_config.get(key)
                    )

        _log.info(
            "Changed robot config, checking for battery parameters: "
            "should_close_adapter=%s, should_cancel_task=%s, disabled=%s",
            should_close_adapter,
            should_cancel_task,
            disabled,
        )
        if should_close_adapter or should_cancel_task or disabled:
            if self._app_loop and self._app_loop.is_running():
                fut = asyncio.run_coroutine_threadsafe(
                    self._cancel_broadcast_task(), self._app_loop
                )
                try:
                    fut.result(timeout=5)
                except Exception as e:
                    _log.error("Error while canceling broadcast task: %s", e)
            else:
                _log.error("App loop is not running-cannot cancel broadcast task.")

        if should_close_adapter or disabled:
            self.close_battery_adapter()

        if not disabled:
            try:
                if should_close_adapter or not self.battery_adapter:
                    self.battery_adapter = self.make_battery_adapter(
                        self.config, bus_manager=self._smbus_manager
                    )
                if should_cancel_task or not self._task:
                    if self._app_loop and self._app_loop.is_running():
                        self._app_loop.call_soon_threadsafe(self._start_broadcast_task)
                    else:
                        _log.error(
                            "App loop is not running-cannot start broadcast task."
                        )
            except Exception as e:
                _log.error("Failed to init battery adapter: %s", e)
                if self._app_loop and self._app_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.connection_manager.error(
                            f"Failed to init battery adapter {e}"
                        ),
                        self._app_loop,
                    )
                else:
                    _log.error(
                        "App loop not running-cannot report error via connection_manager."
                    )

    @staticmethod
    def make_battery_adapter(
        config: HardwareConfig,
        bus_manager: "SMBusManager",
    ) -> Union[
        INA219Battery,
        INA226Battery,
        INA260Battery,
        SunfounderBattery,
        None,
    ]:
        if config.battery is None or not config.battery.enabled:
            return None

        driver = config.battery.driver
        bus = bus_manager.get_bus(driver.bus)
        if isinstance(driver, INA219BatteryDriverConfig):
            return INA219Battery(
                address=driver.addr_int,
                config=driver.to_dataclass(),
                bus=bus,
            )
        elif isinstance(driver, INA226BatteryDriverConfig):
            return INA226Battery(
                address=driver.addr_int,
                config=driver.to_dataclass(),
                bus=bus,
            )
        elif isinstance(driver, INA260BatteryDriverConfig):
            return INA260Battery(
                address=driver.addr_int,
                config=driver.to_dataclass(),
                bus=bus,
            )
        elif isinstance(driver, SunfounderBatteryConfig):
            return SunfounderBattery(
                channel=driver.channel, address=driver.addr_int, bus=bus
            )

    async def read_voltage(self) -> Optional[float]:
        """
        Reads the battery voltage using an ADC (Analog-to-Digital Converter) or uses a cached
        value if the last measurement occurred recently.

        Platform behavior:
        - On a Raspberry Pi, the function uses the actual hardware ADC interface.
        - On other platforms (e.g., local development or testing), it uses a mock ADC implementation.

        Cache behavior:
        To optimize performance and reduce frequent hardware queries, the method employs a caching mechanism.

        If a voltage measurement is requested within the time interval specified by the `BatteryConfig.cache_seconds`
        after the last reading, a cached value is returned instead of performing a new ADC measurement.

        Returns:
            The current battery voltage as a floating-point value, or None if the reading fails.

        Usage:
            ```python
            voltage = await battery_manager.read_voltage()
            print(f"Battery voltage: {voltage}V")
            ```
        """
        if self.config.battery is None:
            return
        if (
            self._last_measure_time is not None
            and (time.time() - self._last_measure_time)
            <= self.config.battery.cache_seconds
        ):
            _log.debug("Using cached voltage value %s", self._last_measure_voltage)
            return self._last_measure_voltage

        value: Optional[float] = None
        if self.battery_adapter is None:
            if (
                self.config.battery
                and self.config.battery.driver
                and self.config.battery.enabled
            ):
                await self.connection_manager.error(
                    "Error reading voltage: no battery adapter"
                )
            return
        async with self._lock:
            try:
                value = await asyncio.to_thread(
                    self.battery_adapter.get_battery_voltage
                )
            except Exception as e:
                _log.error("Error reading voltage: %s", e)
                await self.connection_manager.error(f"Error reading voltage: {e}")

        self._last_measure_time = time.time()
        self._last_measure_voltage = value

        return value

    def setup_connection_manager(self) -> None:
        """
        Subscribes battery monitoring tasks to the events emitted by the WebSocket connection manager.

        On the first active connection, it starts the battery measurement loop, broadcasting
        the battery state to all clients.

        The task is canceled when there are no active connections.
        """
        self.connection_manager.on(
            ConnectionEvent.LAST_CONNECTION.value, self._cancel_broadcast_task
        )
        self.connection_manager.on(
            ConnectionEvent.FIRST_ACTIVE_CONNECTION.value, self._start_broadcast_task
        )

    def close_battery_adapter(self) -> None:
        if self.battery_adapter:
            try:
                _log.info("Closing ADC battery adapter")
                self.battery_adapter.close()
            except Exception as e:
                _log.error("Failed to close ADC battery adapter: %s", e)
            self.battery_adapter = None

    async def cleanup_connection_manager(self) -> None:
        """
        Cancels the battery monitoring task and unsubscribes from the events emitted by the WebSocket
        connection manager.
        """
        self.connection_manager.off(
            ConnectionEvent.FIRST_ACTIVE_CONNECTION.value, self._start_broadcast_task
        )
        self.connection_manager.off(
            ConnectionEvent.LAST_CONNECTION.value, self._cancel_broadcast_task
        )
        await self._cancel_broadcast_task()
        self.close_battery_adapter()

    async def broadcast_state(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Broadcasts the current battery level to all connected clients.
        """
        value: Optional[float] = await self.read_voltage()
        percentage = (
            self._calculate_battery_percentage(value) if value is not None else None
        )

        if value is not None:
            await self.connection_manager.broadcast_json(
                {
                    "type": "battery",
                    "payload": {"voltage": value, "percentage": percentage},
                }
            )

        return (value, percentage)

    def _calculate_battery_percentage(self, voltage: float) -> float:
        """
        Calculates the remaining battery charge as a percentage.

        This value is calculated based on the voltage relative to the battery's
        configured minimum and full voltage levels.

        A value of 0% indicates the voltage is at or below the minimum,
        and 100% indicates it is at the full voltage.
        """
        assert (
            self.config.battery
        ), "Battery config shouldn't be none for calculating percentage"
        adjusted_voltage = max(0, voltage - self.config.battery.min_voltage)
        total_adjusted_voltage = (
            self.config.battery.full_voltage - self.config.battery.min_voltage
        )
        percentage = (adjusted_voltage / total_adjusted_voltage) * 100
        return int(percentage * 10) / 10

    def _start_broadcast_task(self) -> None:
        """
        Starts a background task to periodically broadcast the battery state.
        """
        if (
            self._task is None
            and self.config.battery
            and self.config.battery.enabled
            and self.battery_adapter
        ):
            _log.info("Starting broadcast loop for battery")
            self._task = asyncio.create_task(self._broadcast_loop())

    async def _cancel_broadcast_task(self) -> None:
        """
        Cancels the currently running broadcast task, if active.

        This method unsets the stop event and ensures proper cleanup after
        the task cancellation.
        """

        if self._task:
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
        else:
            _log.info("Skipping cancelling battery task")

    async def _broadcast_loop(self) -> None:
        """
        Asynchronous loop to handle continuous broadcasting of the battery state.
        """
        while (
            not self._stop_event.is_set()
            and self.config.battery
            and self.config.battery.enabled
            and self.battery_adapter
        ):
            (voltage, percentage) = await self.broadcast_state()
            if voltage is None:
                _log.error(
                    "Reading voltage is failed, next measuring after %s",
                    self.config.battery.auto_measure_seconds,
                )
            else:
                if voltage >= self.config.battery.warn_voltage:
                    _log.info(
                        "Battery voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.config.battery.auto_measure_seconds,
                    )
                elif (
                    voltage < self.config.battery.warn_voltage
                    and voltage > self.config.battery.danger_voltage
                ):
                    _log.warning(
                        "Battery voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.config.battery.auto_measure_seconds,
                    )
                elif (
                    voltage < self.config.battery.danger_voltage
                    and voltage > self.config.battery.min_voltage
                ):
                    _log.error(
                        "Danger voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.config.battery.auto_measure_seconds,
                    )
                else:
                    _log.critical(
                        "Critical battery voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.config.battery.auto_measure_seconds,
                    )

            await asyncio.sleep(self.config.battery.auto_measure_seconds)
