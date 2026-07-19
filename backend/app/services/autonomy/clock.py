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


__all__ = ["Clock", "SystemClock"]
