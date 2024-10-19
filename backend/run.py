import multiprocessing as mp
import os
import time
from pathlib import Path

from watchdog.events import (
    EVENT_TYPE_CREATED,
    EVENT_TYPE_DELETED,
    EVENT_TYPE_MODIFIED,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from app.util.proc import terminate_processes


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
            EVENT_TYPE_DELETED,
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


def main():
    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass
    from app.util.reset_mcu_sync import reset_mcu_sync
    from app.util.setup_env import setup_env
    from run_car_control_app import start_control_app
    from run_frontend import start_frontend_app
    from run_main_app import start_main_app

    (
        px_main_app_port,
        px_control_app_port,
        px_log_level,
        px_app_mode,
        px_frontend_port,
    ) = setup_env()

    reset_mcu_sync()
    main_app_process = mp.Process(
        target=start_main_app, args=(px_main_app_port, px_log_level)
    )
    websocket_app_process = mp.Process(
        target=start_control_app, args=(px_control_app_port, px_log_level), daemon=True
    )

    main_app_process.start()
    websocket_app_process.start()

    frontend_dev_process = None
    observer = None
    if px_app_mode == "dev":
        frontend_dev_process = mp.Process(
            target=start_frontend_app,
            args=(px_frontend_port, px_main_app_port, px_control_app_port),
        )
        frontend_dev_process.start()

        def restart_app():
            nonlocal main_app_process, websocket_app_process
            terminate_processes([main_app_process, websocket_app_process])
            main_app_process = mp.Process(
                target=start_main_app, args=(px_main_app_port, px_log_level)
            )
            websocket_app_process = mp.Process(
                target=start_control_app,
                args=(px_control_app_port, px_log_level),
                daemon=True,
            )
            main_app_process.start()
            websocket_app_process.start()
            reload_handler.restart_pending = False

        app_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "app")

        ignore_patterns = ['*.log', 'tmp/*', ".venv", ".pyc", "temp.py"]
        reload_handler = ReloadHandler(restart_app, ignore_patterns=ignore_patterns)
        observer = Observer()
        observer.schedule(reload_handler, path=app_directory, recursive=True)
        observer.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        COLOR_YELLOW = "\033[33m"

        BOLD = "\033[1m"
        RESET = "\033[0m"
        print(
            f"{BOLD}{COLOR_YELLOW}KeyboardInterrupt received. Initiating graceful shutdown...{RESET}"
        )
    finally:
        if observer:
            observer.stop()
            observer.join()
        if frontend_dev_process:
            frontend_dev_process.terminate()
            frontend_dev_process.join()
            frontend_dev_process.close()
        terminate_processes([main_app_process, websocket_app_process])


if __name__ == '__main__':
    main()
