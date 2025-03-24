import asyncio
import multiprocessing as mp
import threading
from typing import TYPE_CHECKING, Optional

from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.managers.distance_manager import distance_process
from app.schemas.distance import UltrasonicConfig

if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized

    from app.core.async_emitter import AsyncEventEmitter, Listener
    from app.managers.async_task_manager import AsyncTaskManager

logger = Logger(__name__, app_name="px_robot")


class DistanceService(metaclass=SingletonMeta):
    def __init__(
        self,
        emitter: "AsyncEventEmitter",
        task_manager: "AsyncTaskManager",
        config: Optional[UltrasonicConfig] = None,
        interval=0.017,
    ):
        self._distance: Synchronized[float] = mp.Value("f", 0)
        self._process = None
        self.config = config or UltrasonicConfig()
        self.stop_event = mp.Event()
        self.interval = interval
        self.lock = threading.Lock()
        self.async_lock = asyncio.Lock()
        self.emitter = emitter
        self.task_manager = task_manager
        self.loading = False

    def subscribe(self, listener: "Listener"):
        self.emitter.on("distance", listener)

    def unsubscribe(self, listener: "Listener"):
        self.emitter.off("distance", listener)

    async def distance_watcher(self):
        initial_value = self._distance.value
        try:
            while (
                hasattr(self, "stop_event")
                and self._process
                and self._process.is_alive()
                and not self.task_manager.stop_event.is_set()
                and not self.stop_event.is_set()
            ):
                if not self.loading:
                    await self.emitter.emit("distance", self.distance)
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
            logger.warning(str(e))
        finally:
            self.loading = False

    async def start_all(self):
        await self.stop_all()
        async with self.async_lock:
            self.loading = True
            await asyncio.to_thread(self._start_process)
            self.task_manager.start_task(
                self.distance_watcher, task_name="distance_watcher"
            )

    async def stop_all(self):
        async with self.async_lock:
            await asyncio.to_thread(self._cancel_process)
            if self.task_manager.task:
                await self.task_manager.cancel_task()

    @property
    def distance(self):
        return round(self._distance.value, 2)

    @property
    def running(self):
        with self.lock:
            return self._process and self._process.is_alive()

    def _start_process(self):
        with self.lock:
            self._process = mp.Process(
                target=distance_process,
                args=(
                    self.config.trig_pin,
                    self.config.echo_pin,
                    self.stop_event,
                    self._distance,
                    self.interval,
                    self.config.timeout,
                ),
            )
            self._process.start()

    def _cancel_process(self):
        with self.lock:
            if self._process is None:
                logger.info("Distance _process is None, skipping stop")
            else:
                self.stop_event.set()

                logger.info("Distance _process setted stop_event")
                self._process.join(10)
                logger.info("Distance _process has been joined")
                if self._process.is_alive():
                    logger.warning(
                        "Force terminating distance _process since it's still alive."
                    )
                    self._process.terminate()
                    self._process.join(5)
                    self._process.close()
            logger.info("Clearing stop event")
            self.stop_event.clear()
            logger.info("Stop event cleared")

    async def cleanup(self) -> None:
        """
        Performs cleanup operations for the distance service, preparing it for shutdown.

        Behavior:
            - Cancels any running tasks and stops the distance _process.
            - Deletes class properties associated with multiprocessing and async state.
        """
        await self.task_manager.cancel_task()
        await asyncio.to_thread(self._cancel_process)
        for prop in [
            "stop_event",
            "_distance",
        ]:
            if hasattr(self, prop):
                logger.info(f"Removing {prop}")
                delattr(self, prop)
