import inspect
import threading
import weakref
from functools import partial
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)

from app.core.logger import Logger

_log = Logger(__name__)

Listener = Union[Callable[..., Any], Callable[..., Awaitable[Any]]]
StoredListener = Union[Listener, weakref.WeakMethod]
EventsMap = Dict[str, List[StoredListener]]

T = TypeVar("T", bound=Listener)


class AsyncEventEmitter:
    """
    An event emitter class that supports both synchronous and asynchronous listeners.
    Automatically supports weak references for bound methods to prevent memory leaks.

    Weak References for Bound Methods:
    - Bound methods (e.g., instance methods like `self.method`) are stored as
      weak references, so that the owning instance (`self`) can be garbage
      collected without lingering listeners.
    - Regular functions (not bound to an instance) are stored as strong references.
    """

    def __init__(self) -> None:
        self.events: EventsMap = {}
        self.lock = threading.Lock()

    @overload
    def on(self, event_name: str, listener: None = ...) -> Callable[[T], T]: ...
    @overload
    def on(self, event_name: str, listener: T) -> T: ...

    def on(
        self, event_name: str, listener: Optional[T] = None
    ) -> Union[T, Callable[[T], T]]:
        """
        Registers a listener for a specific event or can be used as a decorator.

        Supports both regular functions and bound methods. Bound methods are automatically
        wrapped in `weakref.WeakMethod` to prevent memory leaks.

        When no listener is provided, this method acts as a decorator, allowing you to annotate
        functions directly as event listeners.

        Thread-Safety: Thread-safe for concurrent listener registration operations.

        Args:
        --------------
            event_name: The name of the event to subscribe to.
            listener: The listener (function or coroutine) to register. If `None`, this method will return
                      a decorator for annotating functions as listeners.

        Returns:
        --------------
            - When called directly:
                Listener: The same listener that was registered.
            - When used as a decorator:
                Callable[[Listener], Listener]: A decorator function to register the annotated listener.

        Examples:
        --------------
        Using `on` directly to register a listener:
        ```python
        emitter = AsyncEventEmitter()

        def my_listener(data):
            print(f"Received: {data}")

        emitter.on("event_name", my_listener)
        ```

        Using `on` as a decorator:
        ```python
        emitter = AsyncEventEmitter()

        @emitter.on("event_name")
        def my_listener(data):
            print(f"Received: {data}")
        ```
        """
        if listener is None:
            return partial(self.on, event_name)

        with self.lock:
            if event_name not in self.events:
                self.events[event_name] = []

            listener_name = self.get_listener_name(listener)

            resolved_listener = (
                weakref.WeakMethod(listener)
                if hasattr(listener, "__self__") and hasattr(listener, "__func__")
                else listener
            )
            if (
                resolved_listener not in self.events[event_name]
                and listener not in self.events[event_name]
            ):
                self.events[event_name].append(resolved_listener)
                _log.debug(
                    "Added listener '%s' to event '%s'", listener_name, event_name
                )
            else:
                _log.info(
                    "Duplicate listener '%s' not added to event '%s'",
                    listener_name,
                    event_name,
                )

        return listener

    def off(self, event_name: str, listener: Optional[Listener] = None) -> None:
        """
        Removes a specific listener or clears all listeners for an event.

        Args:
        --------------
            event_name: The name of the event to unsubscribe from.
            listener: The specific listener to remove or `None`. If `None`, removes all listeners for the event.

        Example:
        --------------
        ```python
        emitter = AsyncEventEmitter()

        def my_listener(data):
            print(f"Received: {data}")

        emitter.on("event_name", my_listener)
        emitter.off("event_name", my_listener)
        ```
        """
        if event_name not in self.events:
            _log.warning(
                "Attempted to remove a listener from non-existent event '%s'",
                event_name,
            )
            return
        if not listener:
            del self.events[event_name]
            return

        self.events[event_name] = [
            l
            for l in self.events[event_name]
            if AsyncEventEmitter.resolve_listener(l) != listener
        ]
        if not self.events[event_name]:
            del self.events[event_name]

    async def emit(self, event_name: str, *args, **kwargs) -> None:
        """
        Emits the event, invoking all associated listeners with the provided arguments.

        If a listener is a weak reference and its referenced object is garbage collected,
        the listener is automatically removed from the list.

        Args:
        --------------
            event_name: The name of the event to emit.
            *args: Positional arguments to pass to the listeners.
            **kwargs: Keyword arguments to pass to the listeners.

        Example:
        --------------
        ```python
        emitter = AsyncEventEmitter()

        async def my_listener(data):
            print(f"Received: {data}")

        emitter.on("event_name", my_listener)
        await emitter.emit("event_name", "Hello, world!")
        ```
        """
        if event_name not in self.events:
            return
        # Copy to avoid modification during iteration
        for listener_ref in list(self.events[event_name]):
            resolved_listener = AsyncEventEmitter.resolve_listener(listener_ref)
            if not resolved_listener:  # Listener has been garbage collected
                self.events[event_name].remove(listener_ref)
                continue

            listener_name = self.get_listener_name(resolved_listener)

            try:
                _log.debug(
                    "Emitting event '%s' to listener '%s'",
                    event_name,
                    listener_name,
                )
                fn = getattr(resolved_listener, "__func__", resolved_listener)
                if inspect.iscoroutinefunction(fn):
                    await resolved_listener(*args, **kwargs)
                else:
                    resolved_listener(*args, **kwargs)
            except Exception:
                _log.error(
                    "Error running event '%s' listener '%s'",
                    event_name,
                    listener_name,
                    exc_info=True,
                )

    @staticmethod
    def resolve_listener(
        listener: Union[Listener, weakref.WeakMethod]
    ) -> Optional[Listener]:
        """
        Resolves a listener.

        Args:
        --------------
        `listener`: Either a directly referenced listener (function/coroutine)
        or a weak reference (e.g., weakref.WeakMethod).

        Returns:
        --------------
            - For strong references (regular listeners): The listener itself.
            - For weak references: The resolved listener object, if still valid; otherwise `None`.
        """
        if isinstance(listener, weakref.WeakMethod):
            # Resolves the weak reference or returns None if the target is garbage collected
            return listener()
        return listener

    @staticmethod
    def get_listener_name(listener: Listener) -> str:
        """
        Returns the name of the listener.

        Args:
        --------------
        `listener`: A listener function, coroutine, or bound method.

        Returns:
        --------------
        The name of the listener, including the class name for bound methods, or
        a string representation if the name is unavailable.
        """
        return (
            f"{listener.__self__.__class__.__name__}.{listener.__func__.__name__}"
            if inspect.ismethod(listener)
            else getattr(listener, "__name__", str(listener))
        )
