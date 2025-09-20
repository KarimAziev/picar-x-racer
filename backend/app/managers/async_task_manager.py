import asyncio
from typing import Any, Callable, Coroutine, Optional

from app.core.logger import Logger

Worker = Callable[..., Coroutine[Any, Any, Any]]

_log = Logger(__name__)


class AsyncTaskManager:
    def __init__(self):
        self.stop_event = asyncio.Event()
        self.task: Optional[asyncio.Task[Any]] = None
        self.task_name: Optional[str] = None

    def start_task(
        self, worker: Worker, *args: Any, task_name: Optional[str] = None, **kwargs: Any
    ) -> None:
        """
        Starts an asyncio task using the provided worker (async function or coroutine function)
        and optional arguments.
        """
        if asyncio.iscoroutinefunction(worker):
            coroutine = worker(*args, **kwargs)
        else:
            raise TypeError(f"Expected a coroutine function, but got {type(worker)}")

        if self.task is not None and not self.task.done():
            raise RuntimeError(
                "A task is already running. Please cancel it before starting a new one."
            )

        self.task_name = task_name

        self.task = asyncio.create_task(coroutine)

    async def cancel_task(self) -> None:
        """
        Cancels the currently running task, if active.

        This method unsets the stop event and ensures proper cleanup after
        the task cancellation.
        """

        log_prefix = f"task {self.task_name}" if self.task_name else "task"

        if self.task:
            _log.info("Cancelling %s", log_prefix)
            try:
                self.stop_event.set()
                self.task.cancel()
                await self.task
            except asyncio.CancelledError:
                _log.info("Cancelled %s", log_prefix)
                self.task = None
            finally:
                self.stop_event.clear()
        else:
            _log.info("Skipping cancelling %s", log_prefix)
