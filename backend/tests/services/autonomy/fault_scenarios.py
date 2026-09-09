"""Fixed-step, hardware-free sensor delivery scenarios for regression tests."""

from dataclasses import dataclass
import heapq
from typing import Any

from app.services.autonomy.clock import ReplayClock
from app.services.autonomy.topic_bus import Topic, TopicBus, PublishedMessage
from app.services.autonomy.topics import (
    ENCODER_STATE,
    IMU_DATA,
    LIDAR_SCAN,
    STEERING_STATE,
)

SENSOR_TOPICS: dict[str, Topic[Any]] = {
    topic.name: topic for topic in (STEERING_STATE, ENCODER_STATE, IMU_DATA, LIDAR_SCAN)
}


@dataclass(frozen=True)
class DeliveryFault:
    """A half-open interval of acquisition steps; delay never retimestamps data."""

    topic: str
    start_step: int
    end_step: int
    delay_steps: int = 0
    drop: bool = False

    def __post_init__(self) -> None:
        if self.topic not in SENSOR_TOPICS:
            raise ValueError("only simulated sensor topics may be faulted")
        if not 0 <= self.start_step < self.end_step or self.delay_steps < 0:
            raise ValueError(
                "fault interval and delay must be non-negative and ordered"
            )


class SensorDelivery:
    """Bridge two private buses; truth and commands never enter the sensor bus."""

    def __init__(
        self, source: TopicBus, target: TopicBus, faults: tuple[DeliveryFault, ...] = ()
    ) -> None:
        self._observer = source.observe(max_queue_size=64, replay_latest=False)
        self._target = target
        self._faults = faults
        self._pending: list[tuple[int, int, PublishedMessage]] = []
        self._sequence = 0
        self.dropped = 0
        self.delayed = 0
        self.delivered = 0

    def step(self, index: int) -> None:
        while self._observer.pending_messages:
            message = self._observer.get_nowait()
            if message.topic not in SENSOR_TOPICS:
                continue
            active = [
                fault
                for fault in self._faults
                if fault.topic == message.topic
                and fault.start_step <= index < fault.end_step
            ]
            if any(fault.drop for fault in active):
                self.dropped += 1
                continue
            delay = max((fault.delay_steps for fault in active), default=0)
            self.delayed += int(delay > 0)
            heapq.heappush(self._pending, (index + delay, self._sequence, message))
            self._sequence += 1
        if self._observer.dropped_messages:
            raise AssertionError("scenario observer overflowed")
        if len(self._pending) > 4096:
            raise AssertionError("scenario delivery queue exceeded its bound")
        while self._pending and self._pending[0][0] <= index:
            _, _, message = heapq.heappop(self._pending)
            self._target.publish(SENSOR_TOPICS[message.topic], message.message)
            self.delivered += 1

    def close(self) -> None:
        self._observer.close()
        self._pending.clear()


def advance_step(clock: ReplayClock, step: int) -> int:
    timestamp = 1_000_000_000 + step * 20_000_000
    clock.advance_to(timestamp)
    return timestamp
