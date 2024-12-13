import asyncio
import time
from typing import TYPE_CHECKING, Optional

from app.schemas.connection import ConnectionEvent
from app.util.get_battery_voltage import get_battery_voltage as read_battery_voltage
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.files_service import FilesService


class BatteryService(metaclass=SingletonMeta):
    BATTERY_TWO_LEDS_LEVEL = 7.6
    BATTERY_ONE_LEDS_LEVEL = 7.15
    BATTERY_DANGER_LEVEL = 6.5
    BATTERY_MIN_LEVEL = 6.0

    CACHE_SECONDS = 5

    def __init__(
        self, file_manager: "FilesService", connection_manager: "ConnectionService"
    ):
        """
        Initializes the BatteryService with required file and connection services.
        """

        self._logger = Logger(__name__)
        self.connection_manager = connection_manager
        self.settings = file_manager.load_settings()
        self.battery_full_voltage = self.settings.get("battery_full_voltage", 8.4)
        self.battery_auto_measure_seconds = self.settings.get(
            "battery_auto_measure_seconds", 60
        )
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_measure_voltage: Optional[float] = None
        self._last_measure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def read_voltage(self) -> Optional[float]:
        """
        Reads the battery voltage using an ADC (Analog-to-Digital Converter) or uses a cached
        value if the last measurement occurred recently.

        Platform behavior:
        - On a Raspberry Pi, the function uses the actual hardware ADC interface.
        - On other platforms (e.g., local development or testing), it uses a mock ADC implementation.

        Cache behavior:
        To optimize performance and reduce frequent hardware queries, the method employs a caching mechanism.

        If a voltage measurement is requested within the time interval specified by the `CACHE_SECONDS` attribute
        after the last reading, a cached value is returned instead of performing a new ADC measurement.

        Returns:
            The current battery voltage as a floating-point value, or None if the reading fails.

        Usage:
            ```python
            voltage = await battery_manager.read_voltage()
            print(f"Battery voltage: {voltage}V")
            ```
        """
        if (
            self._last_measure_time is not None
            and (time.time() - self._last_measure_time) <= self.CACHE_SECONDS
        ):
            self._logger.debug(
                "Using cached voltage value %s", self._last_measure_voltage
            )
            return self._last_measure_voltage

        value: Optional[float] = None
        async with self._lock:
            try:
                value = await asyncio.to_thread(read_battery_voltage)
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

    async def broadcast_state(self) -> Optional[float]:
        """
        Broadcasts the current battery level to all connected clients.
        """
        value: Optional[float] = await self.read_voltage()

        if value is not None:
            await self.connection_manager.broadcast_json(
                {"type": "battery", "payload": value}
            )

        return value

    def _calculate_battery_percentage(self, voltage: float) -> float:
        """
        Calculates the battery percentage based on the voltage.
        """
        adjusted_voltage = max(0, voltage - self.BATTERY_MIN_LEVEL)
        total_adjusted_voltage = self.battery_full_voltage - self.BATTERY_MIN_LEVEL
        percentage = (adjusted_voltage / total_adjusted_voltage) * 100
        return int(percentage * 10) / 10

    def _start_broadcast_task(self) -> None:
        """
        Starts a background task to periodically broadcast the battery state.
        """
        if self._task is None:
            self._logger.info("Starting broadcast loop")
            self._task = asyncio.create_task(self._broadcast_loop())

    async def _cancel_broadcast_task(self) -> None:
        """
        Cancels the currently running broadcast task, if active.

        This method unsets the stop event and ensures proper cleanup after
        the task cancellation.
        """

        if self._task:
            self._logger.info("Cancelling battery _task")
            try:
                self._stop_event.set()
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                self._logger.info("Battery _task was cancelled")
                self._task = None
            finally:
                self._stop_event.clear()
        else:
            self._logger.info("Skipping cancelling battery _task")

    async def _broadcast_loop(self) -> None:
        """
        Asynchronous loop to handle continuous broadcasting of the battery state.
        """
        while not self._stop_event.is_set():
            voltage = await self.broadcast_state()
            if voltage is None:
                self._logger.error(
                    "Reading voltage is failed, next measuring after %s",
                    self.battery_auto_measure_seconds,
                )
            else:
                percentage = self._calculate_battery_percentage(voltage)
                if voltage >= self.BATTERY_ONE_LEDS_LEVEL:
                    self._logger.info(
                        "Battery voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.battery_auto_measure_seconds,
                    )
                elif (
                    voltage < self.BATTERY_ONE_LEDS_LEVEL
                    and voltage > self.BATTERY_DANGER_LEVEL
                ):
                    self._logger.warning(
                        "Battery voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.battery_auto_measure_seconds,
                    )
                elif (
                    voltage < self.BATTERY_DANGER_LEVEL
                    and voltage > self.BATTERY_MIN_LEVEL
                ):
                    self._logger.error(
                        "Danger voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.battery_auto_measure_seconds,
                    )
                else:
                    self._logger.critical(
                        "Critical battery voltage: %s (%s%%), next measurement after %s",
                        voltage,
                        percentage,
                        self.battery_auto_measure_seconds,
                    )

            await asyncio.sleep(self.battery_auto_measure_seconds)
