"""Await synchronous device operations without abandoning in-flight workers."""

import asyncio
from typing import Callable, ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")


async def run_in_thread(
    function: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs
) -> _R:
    """Keep ownership until the worker finishes, then propagate cancellation.

    Cancelling an asyncio task cannot interrupt synchronous I/O in its worker.
    Draining that worker keeps surrounding resource locks held until device I/O
    has finished, so cleanup can safely close or reconfigure the same device.
    """
    worker = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not worker.cancelled():
            worker.exception()
        raise
