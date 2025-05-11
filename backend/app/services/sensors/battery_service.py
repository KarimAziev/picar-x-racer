import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

from app.core.px_logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.config import (
    HardwareConfig,
    INA219BatteryDriverConfig,
    SunfounderBatteryConfig,
)
from app.schemas.connection import ConnectionEvent
from robot_hat.drivers.adc.INA219 import INA219Config
from robot_hat.services.battery.battery_abc import BatteryABC
from robot_hat.services.battery.sunfounder_battery import Battery as SunfounderBattery
from robot_hat.services.battery.ups_s3_battery import Battery as UPS_S3

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService

_log = Logger(__name__)


class BatteryService(metaclass=SingletonMeta):
    def __init__(
        self,
        connection_manager: "ConnectionService",
        config_manager: "JsonDataManager",
    ):
        """
        Initializes the BatteryService with required file and connection services.
        """

        self.config_manager = config_manager
        self.connection_manager = connection_manager
        self.config = HardwareConfig(**config_manager.load_data())
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_measure_voltage: Optional[float] = None
        self._last_measure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.on(self.config_manager.LOAD_EVENT, self.update_config)
        self.battery_adapter: Optional[BatteryABC] = None
        try:
            self.battery_adapter = self.make_battery_adapter(self.config)
        except Exception as e:
            _log.error("Failed to init battery adapter: %s ", e)

    async def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Updates the robot configuration.

        If the distance process is running, it will be stopped and restarted with the new
        configuration.

        Args:
            new_config: The dictionary with new robot config.
        """
        _log.info("Updating battery config", new_config)
        old_config_dict = self.config.battery.model_dump()
        common_settings_changed = False
        driver_changed = False

        for key, value in old_config_dict.items():
            if key == "driver":
                driver_changed = new_config.get(key) != value
            else:
                common_settings_changed = (
                    common_settings_changed or value != new_config.get(key)
                )

        self.config = HardwareConfig(**new_config)

        if driver_changed or common_settings_changed:
            await self._cancel_broadcast_task()

        if driver_changed or not self.config.battery.enabled:
            self.close_battery_adapter()

        if self.config.battery.enabled:
            try:
                self.battery_adapter = self.make_battery_adapter(self.config)
                if self.battery_adapter:
                    self._start_broadcast_task()
            except Exception as e:
                _log.error("Failed to init battery adapter: %s ", e)
                await self.connection_manager.error(
                    f"Failed to init battery adapter {e}"
                )

    @staticmethod
    def make_battery_adapter(
        config: HardwareConfig,
    ) -> Union[UPS_S3, SunfounderBattery, None]:
        if config.battery is None:
            return None

        driver = config.battery.driver
        if isinstance(driver, INA219BatteryDriverConfig):
            return UPS_S3(
                address=driver.addr_int,
                config=INA219Config(
                    bus_voltage_range=driver.config.bus_voltage_range,
                    gain=driver.config.gain,
                    bus_adc_resolution=driver.config.bus_adc_resolution,
                    shunt_adc_resolution=driver.config.shunt_adc_resolution,
                    mode=driver.config.mode,
                    current_lsb=driver.config.current_lsb,  # 0.1 mA per bit
                    calibration_value=driver.config.calibration_value,
                    power_lsb=driver.config.power_lsb,
                ),
                bus_num=driver.bus,
            )
        elif isinstance(driver, SunfounderBatteryConfig):
            return SunfounderBattery(
                channel=driver.channel, address=driver.addr_int, bus=driver.bus
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
            if self.config.battery and self.config.battery.driver:
                await self.connection_manager.error(
                    "Error reading voltage: no battery adapter"
                )
            return
        async with self._lock:
            try:
                value = await asyncio.to_thread(
                    self.battery_adapter.get_battery_voltage
                )
            except Exception:
                await self.connection_manager.error("Error reading voltage")

        self._last_measure_time = time.time()
        self._last_measure_voltage = value

        return value

    def setup_connection_manager(self):
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

    def close_battery_adapter(self):
        if self.battery_adapter:
            try:
                _log.info("Closing ADC battery adapter")
                self.battery_adapter.close()
            except Exception as e:
                _log.error("Failed to close ADC battery adapter: %s", e)
            self.battery_adapter = None

    async def cleanup_connection_manager(self):
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
        if self._task is None and self.config.battery.enabled and self.battery_adapter:
            _log.info("Starting broadcast loop")
            self._task = asyncio.create_task(self._broadcast_loop())

    async def _cancel_broadcast_task(self) -> None:
        """
        Cancels the currently running broadcast task, if active.

        This method unsets the stop event and ensures proper cleanup after
        the task cancellation.
        """

        if self._task:
            _log.info("Cancelling battery _task")
            try:
                self._stop_event.set()
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                _log.info("Battery _task was cancelled")
            finally:
                self._task = None
                self._stop_event.clear()
        else:
            _log.info("Skipping cancelling battery _task")

    async def _broadcast_loop(self) -> None:
        """
        Asynchronous loop to handle continuous broadcasting of the battery state.
        """
        while (
            not self._stop_event.is_set()
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
