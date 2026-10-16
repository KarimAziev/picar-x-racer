import asyncio
import multiprocessing as mp
import threading
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.core.px_logger import Logger
from app.managers.distance_manager import distance_process
from app.schemas.robot.config import HardwareConfig
from app.util.async_threads import run_in_thread
from app.util.gpio_reservations import validate_distance_pins

if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized

    from app.core.async_emitter import AsyncEventEmitter, Listener
    from app.managers.async_task_manager import AsyncTaskManager
    from app.managers.file_management.json_data_manager import JsonDataManager

_log = Logger(__name__)


class DistanceService:
    def __init__(
        self,
        emitter: "AsyncEventEmitter",
        task_manager: "AsyncTaskManager",
        config_manager: "JsonDataManager",
        interval=0.017,
    ) -> None:

        self.config_manager = config_manager
        self.robot_config = HardwareConfig(**config_manager.load_data())
        self._distance: Synchronized[float] = mp.Value("f", 0)
        self._process = None
        self._closed = False
        self.stop_event = mp.Event()
        self.interval = interval
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()
        self._app_loop: Optional[asyncio.AbstractEventLoop] = None
        self._emitter = emitter
        self._task_manager = task_manager
        self.loading = False
        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.on(self.config_manager.LOAD_EVENT, self.update_config)

    async def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Updates the robot configuration.

        If the distance process is running, it will be stopped and restarted with the new
        configuration.

        Args:
            new_config: The dictionary with new robot config.
        """
        if self._closed:
            return
        _log.info("Updating robot distance config: %s", new_config)
        candidate = HardwareConfig(**new_config)
        loop = asyncio.get_running_loop()
        if (
            self._app_loop
            and self._app_loop.is_running()
            and loop is not self._app_loop
        ):
            await asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(
                    self._apply_config(candidate), self._app_loop
                )
            )
        else:
            await self._apply_config(candidate)

    async def _apply_config(self, config: HardwareConfig) -> None:
        async with self._async_lock:
            if self._closed:
                return
            was_running = self.running
            await self._stop_all_locked()
            with self._lock:
                self.robot_config = config
            if was_running:
                await self._start_all_locked()

    def subscribe(self, listener: "Listener") -> None:
        self._emitter.on("distance", listener)

    def unsubscribe(self, listener: "Listener") -> None:
        self._emitter.off("distance", listener)

    async def distance_watcher(self) -> None:
        initial_value = self._distance.value
        try:
            while (
                hasattr(self, "stop_event")
                and self._process
                and self._process.is_alive()
                and not self._task_manager.stop_event.is_set()
                and not self.stop_event.is_set()
            ):
                if not self.loading:
                    await self._emitter.emit("distance", self.distance)
                    await asyncio.sleep(self.interval)
                elif initial_value == self._distance.value:
                    await asyncio.sleep(self.interval)
                else:
                    self.loading = False

        except (
            BrokenPipeError,
            EOFError,
            ConnectionResetError,
            ConnectionError,
            ConnectionRefusedError,
        ) as e:
            _log.warning(str(e))
        finally:
            self.loading = False

    async def start_all(self) -> None:
        self._app_loop = asyncio.get_running_loop()
        async with self._async_lock:
            await self._stop_all_locked()
            await self._start_all_locked()

    async def _start_all_locked(self) -> None:
        self.loading = True
        try:
            await run_in_thread(self._start_process)
        except BaseException:
            self.loading = False
            raise
        if self.running:
            self._task_manager.start_task(
                self.distance_watcher, task_name="distance_watcher"
            )
        else:
            self.loading = False

    async def stop_all(self) -> None:
        async with self._async_lock:
            await self._stop_all_locked()

    async def _stop_all_locked(self) -> None:
        await run_in_thread(self._cancel_process)
        if self._task_manager.task:
            await self._task_manager.cancel_task()

    @property
    def distance(self) -> float:
        return round(self._distance.value, 2)

    @property
    def running(self) -> Optional[bool]:
        with self._lock:
            return self._process and self._process.is_alive()

    def _start_process(self) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Distance service is shut down")
            if self.robot_config.ultrasonic:
                validate_distance_pins(self.robot_config)
                self._process = mp.Process(
                    target=distance_process,
                    args=(
                        self.robot_config.ultrasonic.trig_pin,
                        self.robot_config.ultrasonic.echo_pin,
                        self.stop_event,
                        self._distance,
                        self.interval,
                        self.robot_config.ultrasonic.timeout,
                    ),
                )
                self._process.start()

    def _cancel_process(self) -> None:
        with self._lock:
            if self._process is None:
                _log.info("No distance process to stop")
            else:
                self.stop_event.set()

                _log.info("Distance process setted stop_event")
                self._process.join(10)
                _log.info("Distance process has been joined")
                if self._process.is_alive():
                    _log.warning(
                        "Force terminating distance process since it's still alive."
                    )
                    self._process.terminate()
                    self._process.join(5)
                if self._process.is_alive():
                    raise RuntimeError("Distance process did not stop")
                self._process.close()
                self._process = None
            _log.info("Clearing stop event")
            self.stop_event.clear()
            _log.info("Stop event cleared")

    async def cleanup(self) -> None:
        """Stop acquisition and reject subsequent attempts to start the service."""
        self._closed = True
        self.config_manager.off(self.config_manager.UPDATE_EVENT, self.update_config)
        self.config_manager.off(self.config_manager.LOAD_EVENT, self.update_config)
        await self.stop_all()
