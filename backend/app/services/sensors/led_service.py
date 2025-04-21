import asyncio
import multiprocessing as mp
import threading
from typing import TYPE_CHECKING, Any, Dict, Union

from app.core.px_logger import Logger
from app.managers.led_manager import led_process
from app.schemas.config import HardwareConfig

if TYPE_CHECKING:
    from app.core.async_emitter import AsyncEventEmitter
    from app.managers.async_task_manager import AsyncTaskManager
    from app.managers.file_management.json_data_manager import JsonDataManager

logger = Logger(__name__)


class LEDService:
    """
    Service to manage a LED process for blinking an LED.

    This service starts a separate process running led_process (from led_manager), which
    simply turns the LED on and off using the configured interval.

    Usage Example:

    # Create instances of AsyncEventEmitter and AsyncTaskManager as required.
    emitter = AsyncEventEmitter()
    task_manager = AsyncTaskManager()

    # Initialize the LED service with configuration, emitter and task manager.
    led_service = LEDService(emitter, task_manager)

    # To start the LED blinking process:
    await led_service.start_all()

    # To stop the LED process:
    await led_service.stop_all()

    # To perform cleanup (e.g., on shutdown), call:
    await led_service.cleanup()
    """

    def __init__(
        self,
        emitter: "AsyncEventEmitter",
        task_manager: "AsyncTaskManager",
        config_manager: "JsonDataManager",
    ):
        self.config_manager = config_manager
        self.robot_config = HardwareConfig(**config_manager.load_data())
        self.led_config = self.robot_config.led
        self.stop_event = mp.Event()
        self.emitter = emitter
        self.task_manager = task_manager
        self._process = None
        self.lock = threading.Lock()
        self.async_lock = asyncio.Lock()
        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.update_config)

        self.config_manager.on(self.config_manager.LOAD_EVENT, self.update_config)

    async def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Updates the robot configuration.

        If the LED process is running, it will be stopped and restarted with the new
        configuration.

        Args:
            new_config: The dictionary with new robot config.
        """
        logger.info("Updating robot led_config", new_config)
        self.robot_config = HardwareConfig(**new_config)
        self.led_config = self.robot_config.led
        if self.running:
            await self.stop_all()
            await self.start_all()

    async def start_all(self):
        """
        Stops any running LED process and starts a new one.

        This method cancels any existing LED process before starting a new one.
        """
        await self.stop_all()
        async with self.async_lock:
            await asyncio.to_thread(self._start_process)

    async def stop_all(self):
        """
        Stops the LED process if it is running.

        This method attempts a graceful shutdown of the LED process.
        """
        async with self.async_lock:
            await asyncio.to_thread(self._cancel_process)

    def _start_process(self):
        """
        Starts the LED process using the led_process function.

        Creates a new multiprocessing.Process to run led_process with the current configuration.
        """
        if self.led_config:
            with self.lock:
                logger.info("Starting LED process")
                self._process = mp.Process(
                    target=led_process,
                    args=(
                        self.led_config.pin,
                        self.stop_event,
                        self.led_config.interval,
                    ),
                )
                self._process.start()

    def _cancel_process(self):
        """
        Cancels the running LED process.

        Sets the stop_event, waits for the process to join and terminates it if still alive.
        """
        with self.lock:
            if self._process is None:
                logger.info("LED _process is None, skipping stop")
            else:
                self.stop_event.set()
                logger.info("LED _process set stop_event")
                self._process.join(10)
                logger.info("LED _process joined")
                if self._process.is_alive():
                    logger.warning(
                        "Force terminating LED _process since it's still alive."
                    )
                    self._process.terminate()
                    self._process.join(5)
                    self._process.close()
            logger.info("Clearing stop event")
            self.stop_event.clear()
            logger.info("Stop event cleared")

    @property
    def running(self) -> bool:
        """
        Returns whether the LED process is currently running.
        """
        with self.lock:
            return self._process is not None and self._process.is_alive()

    async def update_pin(self, new_pin: Union[int, str]) -> None:
        """
        Updates the LED pin.

        The method updates the configuration with new_pin. If the LED process
        is running, it will be stopped and restarted with the new configuration.

        Args:
            new_pin: The new pin (int or str) to use for the LED.
        """
        logger.info("Updating LED pin to %s", new_pin)
        if self.led_config:
            self.led_config.pin = new_pin
        if self.running:
            await self.stop_all()
            await self.start_all()

    async def update_interval(self, new_interval: float) -> None:
        """
        Updates the LED blink interval.

        The method updates the configuration with new_interval. If the LED process
        is running, it will be stopped and restarted with the new configuration.

        Args:
            new_interval: The new interval (in seconds) for blinking.
        """
        logger.info("Updating LED interval to %s", new_interval)
        if self.led_config:
            self.led_config.interval = new_interval
        if self.running:
            await self.stop_all()
            await self.start_all()

    async def cleanup(self) -> None:
        """
        Performs cleanup operations needed for LED service shutdown.

        This method stops the running LED process and removes associated properties
        to aid in graceful shutdown.

        Usage:
            await led_service.cleanup()
        """
        await self.stop_all()
        for prop in ["stop_event", "_process"]:
            if hasattr(self, prop):
                logger.info(f"Removing {prop}")
                delattr(self, prop)
