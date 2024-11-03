import os
from pathlib import Path

from watchdog.events import (
    EVENT_TYPE_CREATED,
    EVENT_TYPE_MODIFIED,
    EVENT_TYPE_MOVED,
    FileSystemEventHandler,
)


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, callback, ignore_patterns=None):
        super().__init__()
        self.callback = callback
        self.restart_pending = False
        self.ignore_patterns = ignore_patterns or []

    def on_any_event(self, event):
        file_name = event.src_path
        if event.event_type in [
            EVENT_TYPE_MODIFIED,
            EVENT_TYPE_CREATED,
            EVENT_TYPE_MOVED,
        ]:
            if not isinstance(file_name, str) or not Path(file_name).suffix == '.py':
                return

            if any(file_name.endswith(pattern) for pattern in self.ignore_patterns):
                return

            file_name_base = os.path.basename(file_name)

            if not self.restart_pending:
                self.restart_pending = True
                print(
                    f"File change detected in {file_name_base}. Restarting application..."
                )
                self.callback()
