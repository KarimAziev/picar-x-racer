from __future__ import annotations

import asyncio
import threading
from functools import wraps
from typing import Any, Awaitable, Callable

from typing_extensions import ParamSpec

P = ParamSpec("P")


def async_debounce(
    wait: float,
) -> Callable[[Callable[P, Awaitable[Any]]], Callable[P, Awaitable[None]]]:
    """
    A decorator that debounces an async function.

    The function execution is delayed until no new calls occur for 'wait' seconds.

    All callers awaiting a debounced call will receive the result of the final execution.

    Usage:

      @debounce(0.5)
      async def my_func(arg):
          ...

      # Multiple calls within 0.5 seconds will only result in one execution.
      result = await my_func(10)

    """

    def decorator(func):
        lock = asyncio.Lock()
        timer_handle = None
        pending_future = None
        last_args = None
        last_kwargs = None

        @wraps(func)
        async def debounced(*args, **kwargs):
            nonlocal timer_handle, pending_future, last_args, last_kwargs

            loop = asyncio.get_running_loop()

            async with lock:
                last_args = args
                last_kwargs = kwargs

                if timer_handle is not None:
                    timer_handle.cancel()

                if pending_future is None or pending_future.done():
                    pending_future = loop.create_future()

                timer_handle = loop.call_later(
                    wait, lambda: asyncio.create_task(execute())
                )

                return await pending_future

        async def execute():
            nonlocal timer_handle, pending_future, last_args, last_kwargs
            try:
                result = await func(*(last_args or ()), **(last_kwargs or {}))
            except Exception as exc:
                async with lock:
                    if pending_future is not None and not pending_future.done():
                        pending_future.set_exception(exc)
                    timer_handle = None
                return

            async with lock:
                if pending_future is not None and not pending_future.done():
                    pending_future.set_result(result)
                timer_handle = None

        return debounced

    return decorator


def debounce(wait: float) -> Callable[[Callable[P, Any]], Callable[P, None]]:
    """
    A decorator that will debounce calls to the decorated function for `wait` seconds.

    Args:
    --------------
        `wait`: Time to wait in seconds before executing the function.

    Returns:
    --------------
        The decorator that wraps the function/method.

    Note:
    --------------
        Because this implementation schedules the real function call on a timer thread,
        the wrapped function effectively returns None from the caller's perspective,
        even if the original function had a different return type.

    Usage:
    --------------
    ```python
    @debounce(1.0)
    def my_function(x: int) -> None:
        print(f"Debounced call with x={x}")
    ```
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, None]:
        timer: threading.Timer | None = None

        @wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> None:
            nonlocal timer

            if timer is not None:
                timer.cancel()

            def run() -> None:
                func(*args, **kwargs)

            timer = threading.Timer(wait, run)
            timer.start()

        return wrapped

    return decorator
