import os
from pathlib import Path
from threading import Timer
from typing import List

from watchdog.events import (
    EVENT_TYPE_CREATED,
    EVENT_TYPE_MODIFIED,
    EVENT_TYPE_MOVED,
    FileSystemEventHandler,
)


class ReloadHandler(FileSystemEventHandler):
    def __init__(
        self, callback, ignore_patterns: List[str] = [], debounce_duration=2
    ) -> None:
        """
        :param callback: The function to be called when a file change is detected
        :param ignore_patterns: List of file patterns to be ignored (e.g., ['test.py'])
        :param debounce_duration: Time in seconds to debounce the callback
        """
        super().__init__()
        self.callback = callback
        self.ignore_patterns = ignore_patterns
        self.debounce_duration = debounce_duration
        self.restart_pending = False
        self._debounce_timer = None

    def _debounce_restart(self, file_name: str) -> None:
        """Call the callback after debounce delay."""
        file_name_base = os.path.basename(file_name)
        print(f"File change detected in {file_name_base}. Restarting application...")
        self.restart_pending = True
        self.callback()

    def on_any_event(self, event) -> None:
        file_name = event.src_path

        if event.event_type in [
            EVENT_TYPE_MODIFIED,
            EVENT_TYPE_CREATED,
            EVENT_TYPE_MOVED,
        ]:
            if not isinstance(file_name, str) or not Path(file_name).suffix == ".py":
                return

            if any(file_name.endswith(pattern) for pattern in self.ignore_patterns):
                return

            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None

            self._debounce_timer = Timer(
                self.debounce_duration, self._debounce_restart, [file_name]
            )
            self._debounce_timer.start()
