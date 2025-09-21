import asyncio
import multiprocessing as mp
import threading
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.core.px_logger import Logger
from app.managers.distance_manager import distance_process
from app.schemas.robot.config import HardwareConfig

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
        self.stop_event = mp.Event()
        self.interval = interval
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
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
        _log.info("Updating robot distance config", new_config)
        self.robot_config = HardwareConfig(**new_config)
        if self.running:
            await self.stop_all()
            await self.start_all()

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
        await self.stop_all()
        async with self._async_lock:
            self.loading = True
            await asyncio.to_thread(self._start_process)
            self._task_manager.start_task(
                self.distance_watcher, task_name="distance_watcher"
            )

    async def stop_all(self) -> None:
        async with self._async_lock:
            await asyncio.to_thread(self._cancel_process)
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
        if self.robot_config.ultrasonic:
            with self._lock:
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
                    self._process.close()
            _log.info("Clearing stop event")
            self.stop_event.clear()
            _log.info("Stop event cleared")

    async def cleanup(self) -> None:
        """
        Performs cleanup operations for the distance service, preparing it for shutdown.

        Behavior:
            - Cancels any running tasks and stops the distance _process.
            - Deletes class properties associated with multiprocessing and async state.
        """
        await self._task_manager.cancel_task()
        await asyncio.to_thread(self._cancel_process)
        async with self._async_lock:
            with self._lock:
                self.__dict__.pop("stop_event", None)
                self.__dict__.pop("_process", None)
                self.__dict__.pop("_distance", None)
