import asyncio
from typing import TYPE_CHECKING, Optional

from app.util.get_battery_voltage import get_battery_voltage as read_battery_voltage
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.files_service import FilesService


class BatteryService(metaclass=SingletonMeta):
    BATTERY_MIN_LEVEL = 6.0
    POLL_SHORT_INTERVAL = 60  # 1 minute
    POLL_LONG_INTERVAL = 5 * 60  # 5 minutes
    POLL_EXTRA_SHORT_INTERVAL = 30  # 30 seconds

    def __init__(
        self, file_manager: "FilesService", connection_manager: "ConnectionService"
    ):
        """
        Initializes the BatteryService with required file and connection services.
        """

        self.logger = Logger(__name__)
        self.connection_manager = connection_manager
        self.settings = file_manager.load_settings()
        self.battery_full_voltage = self.settings.get("battery_full_voltage", 8.4)
        self.stop_event = asyncio.Event()
        self.task: Optional[asyncio.Task] = None
        self.lock = asyncio.Event()

    async def cancel_broadcast_task(self) -> None:
        """
        Cancels the currently running broadcast task, if active.

        This method unsets the stop event and ensures proper cleanup after
        the task cancellation.
        """

        if self.task:
            self.logger.info("Cancelling battery task")
            try:
                self.stop_event.set()
                self.task.cancel()
                await self.task
            except asyncio.CancelledError:
                self.logger.info("Music battery task was cancelled")
                self.task = None
            finally:
                self.stop_event.clear()
        else:
            self.logger.info("Skipping cancelling battery task")

    async def broadcast_state(self) -> Optional[float]:
        """
        Broadcasts the current battery level to all connected clients.
        """
        value: Optional[float] = None
        try:
            value = await asyncio.to_thread(read_battery_voltage)
        except Exception:
            await self.connection_manager.error("Error reading voltage")

        if value is not None:
            await self.connection_manager.broadcast_json(
                {"type": "battery", "payload": value}
            )

        return value

    def calculate_battery_percentage(self, voltage: float) -> float:
        """
        Calculates the battery percentage based on the voltage.
        """
        adjusted_voltage = max(0, voltage - self.BATTERY_MIN_LEVEL)
        total_adjusted_voltage = self.battery_full_voltage - self.BATTERY_MIN_LEVEL
        return (adjusted_voltage / total_adjusted_voltage) * 100

    def determine_poll_interval(self, percentage: float) -> int:
        """
        Determines the polling interval based on the battery percentage.
        """
        return self.POLL_SHORT_INTERVAL if percentage < 20 else self.POLL_LONG_INTERVAL

    def start_broadcast_task(self) -> None:
        """
        Starts a background task to periodically broadcast the battery state.
        """
        self.task = asyncio.create_task(self.broadcast_loop())

    async def broadcast_loop(self) -> None:
        """
        Asynchronous loop to handle continuous broadcasting of the battery state.
        """
        while not self.stop_event.is_set():
            has_clients = len(self.connection_manager.active_connections) > 0
            interval = (
                self.POLL_LONG_INTERVAL
                if has_clients
                else self.POLL_EXTRA_SHORT_INTERVAL
            )
            try:
                if has_clients:
                    voltage = await self.broadcast_state()
                    if voltage is not None:
                        self.logger.info("ADC voltage %s", voltage)
                        percentage = self.calculate_battery_percentage(voltage)
                        interval = self.determine_poll_interval(percentage)
                        if percentage < 5:
                            self.logger.warning(
                                "Low ADC level %s%%, (voltage: %s)",
                                int(percentage * 10) / 10,
                                voltage,
                            )
            except Exception:
                self.logger.error("Error in battery broadcast loop", exc_info=True)

            await asyncio.sleep(interval)
