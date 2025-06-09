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
    An async decorator that will debounce calls to the decorated async function
    for `wait` seconds.

    Args:
    --------------
    `wait`: Time to wait in seconds before executing the wrapped async function.

    Returns:
    --------------
    The decorator that wraps the async function.

    Note:
    --------------
    Because the underlying call is scheduled on a separate async task, the decorated
    function returns a coroutine that immediately completes (returning None),
    while the real work runs later in the event loop.
    """

    def decorator(func: Callable[P, Awaitable[Any]]) -> Callable[P, Awaitable[None]]:
        task: asyncio.Task[Any] | None = None
        last_args: tuple[Any, ...] | None = None
        last_kwargs: dict[str, Any] | None = None

        async def scheduled_call() -> None:
            await asyncio.sleep(wait)
            if last_args is not None and last_kwargs is not None:
                await func(*last_args, **last_kwargs)

        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> None:
            nonlocal task, last_args, last_kwargs
            last_args = args
            last_kwargs = kwargs

            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            task = asyncio.create_task(scheduled_call())

        return wrapped

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
