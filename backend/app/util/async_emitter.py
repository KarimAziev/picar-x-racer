import asyncio
from typing import Any, Awaitable, Callable, Optional, Union

from app.util.logger import Logger

logger = Logger(__name__)

Listener = Union[Callable[..., Any], Callable[..., Awaitable[Any]]]


class AsyncEventEmitter:
    def __init__(self):
        self.events = {}

    def on(self, event_name: str, listener: Listener):
        """Registers an event listener for the given event name.

        Can be used as:
        - A direct method: `on(event_name, listener)`
        - A decorator: `@on(event_name)`
        """
        if listener is None:
            return partial(self.on, event_name)

        if event_name not in self.events:
            self.events[event_name] = []
        self.events[event_name].append(listener)
        return listener

    def off(self, event_name: str, listener: Optional[Listener] = None):
        """Removes a specific listener or all listeners for an event."""
        if listener is None:
            if event_name in self.events:
                del self.events[event_name]
        else:
            if event_name in self.events and listener in self.events[event_name]:
                self.events[event_name].remove(listener)
                if not self.events[event_name]:
                    del self.events[event_name]

    async def emit(self, event_name: str, *args, **kwargs):
        """Invokes all listeners associated with the named event."""
        if event_name in self.events:
            for listener in self.events[event_name]:
                if listener is not None:
                    listener_name = (
                        listener.__name__
                        if hasattr(listener, "__name__")
                        else str(listener)
                    )
                    try:
                        logger.info(
                            "Emitting event '%s' to listener '%s'",
                            event_name,
                            listener_name,
                        )
                        if asyncio.iscoroutinefunction(listener):
                            await listener(*args, **kwargs)
                        else:
                            listener(*args, **kwargs)

                    except Exception:
                        logger.error(
                            "Error running event '%s' listener '%s'",
                            event_name,
                            listener_name,
                            exc_info=True,
                        )
