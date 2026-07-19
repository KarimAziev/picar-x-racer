"""Typed, bounded, non-blocking topics for high-rate robot data."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, Set, Type, TypeVar, Union, cast


T = TypeVar("T")
_CLOSED = object()


class TopicDefinitionError(ValueError):
    """Raised when one topic name is registered with incompatible metadata."""


class SubscriptionClosed(RuntimeError):
    """Raised when reading from a closed topic subscription."""


@dataclass(frozen=True)
class Topic(Generic[T]):
    name: str
    message_type: Type[T]
    retain_latest: bool = True

    def __post_init__(self) -> None:
        if not self.name.startswith("/") or self.name == "/":
            raise ValueError("topic name must be an absolute non-root path")
        if "//" in self.name or self.name.endswith("/"):
            raise ValueError("topic name must not contain empty path components")


@dataclass(frozen=True)
class TopicStats:
    published_messages: int
    delivered_messages: int
    dropped_messages: int
    subscribers: int


@dataclass
class _MutableTopicStats:
    published_messages: int = 0
    delivered_messages: int = 0
    dropped_messages: int = 0


class TopicSubscription(Generic[T]):
    """One consumer's independent bounded queue."""

    def __init__(
        self,
        bus: "TopicBus",
        topic: Topic[T],
        max_queue_size: int,
    ) -> None:
        self.topic = topic
        self._bus = bus
        self._queue: asyncio.Queue[Union[T, object]] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self._closed = False
        self.dropped_messages = 0

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def pending_messages(self) -> int:
        return self._queue.qsize()

    async def get(self) -> T:
        item = await self._queue.get()
        if item is _CLOSED:
            raise SubscriptionClosed(f"subscription to {self.topic.name} is closed")
        return cast(T, item)

    def get_nowait(self) -> T:
        item = self._queue.get_nowait()
        if item is _CLOSED:
            raise SubscriptionClosed(f"subscription to {self.topic.name} is closed")
        return cast(T, item)

    def close(self) -> None:
        self._bus._close_subscription(self)

    def __aiter__(self) -> "TopicSubscription[T]":
        return self

    async def __anext__(self) -> T:
        try:
            return await self.get()
        except SubscriptionClosed as error:
            raise StopAsyncIteration from error

    def _offer(self, message: T) -> bool:
        if self._closed:
            return False
        dropped = False
        if self._queue.full():
            self._queue.get_nowait()
            self.dropped_messages += 1
            dropped = True
        self._queue.put_nowait(message)
        return dropped

    def _mark_closed(self) -> None:
        if self._closed:
            return
        self._closed = True
        while not self._queue.empty():
            self._queue.get_nowait()
        self._queue.put_nowait(_CLOSED)


class TopicBus:
    """Fan out messages without allowing slow consumers to block producers."""

    def __init__(self) -> None:
        self._topics: Dict[str, Topic[Any]] = {}
        self._subscriptions: Dict[str, Set[TopicSubscription[Any]]] = {}
        self._latest: Dict[str, Any] = {}
        self._stats: Dict[str, _MutableTopicStats] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._closed = False

    def subscribe(
        self,
        topic: Topic[T],
        *,
        max_queue_size: int = 1,
        replay_latest: bool = True,
    ) -> TopicSubscription[T]:
        if self._closed:
            raise RuntimeError("topic bus is closed")
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be greater than zero")
        self._bind_running_loop()
        self._register_topic(topic)
        subscription = TopicSubscription(self, topic, max_queue_size)
        self._subscriptions.setdefault(topic.name, set()).add(subscription)
        if replay_latest and topic.name in self._latest:
            subscription._offer(cast(T, self._latest[topic.name]))
        return subscription

    def publish(self, topic: Topic[T], message: T) -> None:
        if self._closed:
            raise RuntimeError("topic bus is closed")
        self._bind_running_loop()
        self._register_topic(topic)
        if not isinstance(message, topic.message_type):
            raise TypeError(
                f"topic {topic.name} requires {topic.message_type.__name__}, "
                f"got {type(message).__name__}"
            )

        stats = self._stats[topic.name]
        stats.published_messages += 1
        if topic.retain_latest:
            self._latest[topic.name] = message
        for subscription in tuple(self._subscriptions.get(topic.name, ())):
            dropped = subscription._offer(message)
            stats.delivered_messages += 1
            if dropped:
                stats.dropped_messages += 1

    def publish_threadsafe(self, topic: Topic[T], message: T) -> None:
        """Schedule publication from a sensor thread onto the bus event loop."""

        loop = self._loop
        if loop is None:
            raise RuntimeError("topic bus must be used on its event loop first")
        loop.call_soon_threadsafe(self.publish, topic, message)

    def latest(self, topic: Topic[T]) -> Optional[T]:
        self._register_topic(topic)
        return cast(Optional[T], self._latest.get(topic.name))

    def stats(self, topic: Topic[Any]) -> TopicStats:
        self._register_topic(topic)
        stats = self._stats[topic.name]
        return TopicStats(
            published_messages=stats.published_messages,
            delivered_messages=stats.delivered_messages,
            dropped_messages=stats.dropped_messages,
            subscribers=len(self._subscriptions.get(topic.name, ())),
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for subscriptions in tuple(self._subscriptions.values()):
            for subscription in tuple(subscriptions):
                subscription._mark_closed()
        self._subscriptions.clear()

    def _bind_running_loop(self) -> None:
        loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = loop
        elif self._loop is not loop:
            raise RuntimeError("topic bus cannot span multiple event loops")

    def _register_topic(self, topic: Topic[Any]) -> None:
        existing = self._topics.get(topic.name)
        if existing is not None and existing != topic:
            raise TopicDefinitionError(
                f"topic {topic.name} already has a different definition"
            )
        if existing is None:
            self._topics[topic.name] = topic
            self._stats[topic.name] = _MutableTopicStats()

    def _close_subscription(self, subscription: TopicSubscription[Any]) -> None:
        subscriptions = self._subscriptions.get(subscription.topic.name)
        if subscriptions is not None:
            subscriptions.discard(subscription)
            if not subscriptions:
                self._subscriptions.pop(subscription.topic.name, None)
        subscription._mark_closed()


__all__ = [
    "SubscriptionClosed",
    "Topic",
    "TopicBus",
    "TopicDefinitionError",
    "TopicStats",
    "TopicSubscription",
]
