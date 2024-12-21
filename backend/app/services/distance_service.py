import asyncio
import multiprocessing as mp
import threading
from typing import TYPE_CHECKING

from app.util.distance_process import distance_process
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized

    from app.services.async_task_manager import AsyncTaskManager
    from app.util.async_emitter import AsyncEventEmitter, Listener

logger = Logger(__name__)


class DistanceService(metaclass=SingletonMeta):
    def __init__(
        self,
        emitter: "AsyncEventEmitter",
        task_manager: "AsyncTaskManager",
        echo_pin: str = "D2",
        trig_pin: str = "D3",
        interval=0.017,
        timeout=0.017,
    ):
        self.distance: Synchronized[float] = mp.Value('f', 0)
        self.process = None
        self.stop_event = mp.Event()
        self.echo_pin = echo_pin
        self.trig_pin = trig_pin
        self.interval = interval
        self.timeout = timeout
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
        initial_value = self.distance.value
        try:
            while (
                hasattr(self, "stop_event")
                and self.process
                and self.process.is_alive()
                and not self.task_manager.stop_event.is_set()
                and not self.stop_event.is_set()
            ):
                if not self.loading:
                    distance = self.distance.value
                    await self.emitter.emit("distance", distance)
                    await asyncio.sleep(self.interval)
                elif initial_value == self.distance.value:
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
            await asyncio.to_thread(self.start_process)
            self.task_manager.start_task(
                self.distance_watcher, task_name="distance_watcher"
            )

    @property
    def running(self):
        with self.lock:
            return self.process and self.process.is_alive()

    async def stop_all(self):
        async with self.async_lock:
            await asyncio.to_thread(self.cancel_process)
            if self.task_manager.task:
                await self.task_manager.cancel_task()

    def start_process(self):
        with self.lock:
            self.process = mp.Process(
                target=distance_process,
                args=(
                    self.echo_pin,
                    self.trig_pin,
                    self.stop_event,
                    self.distance,
                    self.interval,
                    self.timeout,
                ),
            )
            self.process.start()

    def cancel_process(self):
        with self.lock:
            if self.process is None:
                logger.info("Distance process is None, skipping stop")
            else:
                self.stop_event.set()

                logger.info("Distance process setted stop_event")
                self.process.join(10)
                logger.info("Distance process has been joined")
                if self.process.is_alive():
                    logger.warning(
                        "Force terminating distance process since it's still alive."
                    )
                    self.process.terminate()
                    self.process.join(5)
                    self.process.close()
            logger.info("Clearing stop event")
            self.stop_event.clear()
            logger.info("Stop event cleared")

    async def cleanup(self) -> None:
        """
        Performs cleanup operations for the distance service, preparing it for shutdown.

        Behavior:
            - Cancels any running tasks and stops the distance process.
            - Deletes class properties associated with multiprocessing and async state.
        """
        await self.task_manager.cancel_task()
        await asyncio.to_thread(self.cancel_process)
        for prop in [
            "stop_event",
            "distance",
        ]:
            if hasattr(self, prop):
                logger.info(f"Removing {prop}")
                delattr(self, prop)
