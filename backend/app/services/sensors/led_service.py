import multiprocessing as mp
import threading
from contextlib import AbstractContextManager, nullcontext
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from app.core.px_logger import Logger
from app.managers.led_manager import led_process
from app.schemas.robot.config import HardwareConfig
from app.util.async_threads import run_in_thread
from app.util.gpio_reservations import gpio_number, validate_led_pin

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event

    from app.adapters.picarx_adapter import PicarxAdapter
    from app.core.async_emitter import AsyncEventEmitter
    from app.managers.async_task_manager import AsyncTaskManager
    from app.managers.file_management.json_data_manager import JsonDataManager

_log = Logger(__name__)


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
    ) -> None:
        self.config_manager = config_manager
        self.robot_config = HardwareConfig(**config_manager.load_data())
        self.led_config = self.robot_config.led
        self.stop_event: Optional[Event] = mp.Event()
        self.emitter = emitter
        self.task_manager = task_manager
        self._process = None
        self._closed = False
        self.lock = threading.RLock()
        self._hardware: Union["PicarxAdapter", None] = None
        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.update_config)

        self.config_manager.on(self.config_manager.LOAD_EVENT, self.update_config)

    def bind_hardware(self, hardware: "PicarxAdapter") -> None:
        """Serialize GPIO claims with actuator initialization and shutdown."""
        self._hardware = hardware

    def _hardware_session(self) -> AbstractContextManager[None]:
        return self._hardware.hardware_session() if self._hardware else nullcontext()

    def _validate_pin(self, pin: Union[int, str]) -> None:
        config = self.robot_config
        if self._hardware is not None:
            config = config.model_copy(
                update={
                    name: getattr(self._hardware.config, name)
                    for name in (
                        "motors",
                        "steering_servo",
                        "cam_pan_servo",
                        "cam_tilt_servo",
                    )
                }
            )
        validate_led_pin(config, pin)

    async def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Updates the robot configuration.

        If the LED process is running, it will be stopped and restarted with the new
        configuration.

        Args:
            new_config: The dictionary with new robot config.
        """
        await run_in_thread(self._update_config, new_config)

    def _update_config(self, new_config: Dict[str, Any]) -> None:
        with self.lock:
            if self._closed:
                return
            was_running = self.running
            self._cancel_process()
            with self._hardware_session():
                self.robot_config = HardwareConfig(**new_config)
                self.led_config = self.robot_config.led
                if was_running:
                    self._start_process()

    async def start_all(self) -> None:
        """
        Stops any running LED process and starts a new one.

        This method cancels any existing LED process before starting a new one.
        """
        await run_in_thread(self._restart_process)

    def _restart_process(self) -> None:
        with self.lock:
            self._cancel_process()
            self._start_process()

    async def stop_all(self) -> None:
        """
        Stops the LED process if it is running.

        This method attempts a graceful shutdown of the LED process.
        """
        await run_in_thread(self._cancel_process)

    def _start_process(self) -> None:
        """
        Starts the LED process using the led_process function.

        Creates a new multiprocessing.Process to run led_process with the current configuration.
        """
        with self.lock, self._hardware_session():
            if self._closed:
                raise RuntimeError("LED service is shut down")
            if self.led_config:
                self._validate_pin(self.led_config.pin)
                _log.info("Starting LED process")
                self._process = mp.Process(
                    target=led_process,
                    args=(
                        gpio_number(self.led_config.pin),
                        self.stop_event,
                        self.led_config.interval,
                    ),
                )
                self._process.start()

    def _cancel_process(self) -> None:
        """
        Cancels the running LED process.

        Sets the stop_event, waits for the process to join and terminates it if still alive.
        """
        with self.lock:
            if self.stop_event is None:
                return
            if self._process is None:
                _log.info("No LED process to stop")
            else:
                self.stop_event.set()
                _log.info("LED process set stop_event")
                self._process.join(10)
                _log.info("LED process joined")
                if self._process.is_alive():
                    _log.warning(
                        "Force terminating LED process since it's still alive."
                    )
                    self._process.terminate()
                    self._process.join(5)
                if self._process.is_alive():
                    raise RuntimeError("LED process did not stop")
                self._process.close()
                self._process = None
            _log.info("Clearing stop event")
            self.stop_event.clear()
            _log.info("Stop event cleared")

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
        _log.info("Updating LED pin to %s", new_pin)
        await run_in_thread(self._update_pin, new_pin)

    def _update_pin(self, new_pin: Union[int, str]) -> None:
        with self.lock:
            was_running = self.running
            if was_running:
                self._cancel_process()
            with self._hardware_session():
                if self._closed:
                    raise RuntimeError("LED service is shut down")
                self._validate_pin(new_pin)
                if self.led_config:
                    self.led_config.pin = new_pin
                if was_running:
                    self._start_process()

    async def update_interval(self, new_interval: float) -> None:
        """
        Updates the LED blink interval.

        The method updates the configuration with new_interval. If the LED process
        is running, it will be stopped and restarted with the new configuration.

        Args:
            new_interval: The new interval (in seconds) for blinking.
        """
        _log.info("Updating LED interval to %s", new_interval)
        await run_in_thread(self._update_interval, new_interval)

    def _update_interval(self, new_interval: float) -> None:
        with self.lock:
            was_running = self.running
            if was_running:
                self._cancel_process()
            if self.led_config:
                self.led_config.interval = new_interval
            if was_running:
                self._start_process()

    async def cleanup(self) -> None:
        """Stop the worker and release IPC resources before process exit."""
        self._closed = True
        self.config_manager.off(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.off(self.config_manager.LOAD_EVENT, self.update_config)
        await run_in_thread(self._cleanup_resources)

    def _cleanup_resources(self) -> None:
        with self.lock:
            self._cancel_process()
            # Cached services can outlive lifespan shutdown. Dropping this event
            # unlinks its semaphores before Uvicorn replays SIGTERM.
            self.stop_event = None
