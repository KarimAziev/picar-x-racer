"""Clock abstractions used by autonomy-domain control logic."""

import time
from typing import Protocol


class Clock(Protocol):
    """Provide monotonic time for command validity and watchdog decisions."""

    def monotonic_ns(self) -> int:
        """Return monotonic time in nanoseconds."""
        ...


class SystemClock:
    """Clock backed by the operating system's monotonic clock."""

    def monotonic_ns(self) -> int:
        return time.monotonic_ns()


class ReplayClock:
    """Explicit monotonic time advanced by recorded publication timestamps."""

    def __init__(self) -> None:
        self._now_ns = 0

    def monotonic_ns(self) -> int:
        return self._now_ns

    def advance_to(self, timestamp_ns: int) -> None:
        if timestamp_ns < self._now_ns:
            raise ValueError("replay timestamps must not go backwards")
        self._now_ns = timestamp_ns


__all__ = ["Clock", "SystemClock"]
