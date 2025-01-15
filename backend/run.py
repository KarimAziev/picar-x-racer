import os
import time
from typing import Optional

from app.util.proc import terminate_processes


def main():
    import multiprocessing as mp

    try:
        mp.set_start_method("spawn")
    except RuntimeError:
        pass
    from dotenv import load_dotenv
    from robot_hat import reset_mcu_sync

    from app.util.setup_env import setup_env
    from run_car_control_app import start_control_app
    from run_frontend import start_frontend_app
    from run_main_app import start_main_app

    main_app_process: Optional["mp.Process"] = None
    websocket_app_process: Optional["mp.Process"] = None
    frontend_dev_process: Optional["mp.Process"] = None
    observer = None

    try:
        env_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.env')

        if os.path.exists(env_file):
            print(f"Loading .env {env_file}")
            load_dotenv(env_file, verbose=True)

        (
            px_main_app_port,
            px_control_app_port,
            px_log_level,
            px_app_mode,
            px_frontend_port,
        ) = setup_env()

        reset_mcu_sync()
        main_app_process = mp.Process(
            target=start_main_app,
            args=(px_main_app_port, px_log_level),
            name="px_main_server",
        )
        websocket_app_process = mp.Process(
            target=start_control_app,
            args=(px_control_app_port, px_log_level),
            name="px_control_server",
        )

        main_app_process.start()
        websocket_app_process.start()

        frontend_dev_process = None
        if px_app_mode == "dev":
            from watchdog.events import (
                FileCreatedEvent,
                FileModifiedEvent,
                FileMovedEvent,
            )
            from watchdog.observers import Observer

            from app.adapters.reload_handler import ReloadHandler

            frontend_dev_process = mp.Process(
                target=start_frontend_app,
                args=(px_frontend_port, px_main_app_port, px_control_app_port),
            )
            frontend_dev_process.start()

            def restart_app():
                nonlocal main_app_process, websocket_app_process
                terminate_processes([websocket_app_process, main_app_process])
                main_app_process = mp.Process(
                    target=start_main_app,
                    args=(px_main_app_port, px_log_level),
                    name="px_main_server",
                )
                websocket_app_process = mp.Process(
                    target=start_control_app,
                    args=(px_control_app_port, px_log_level),
                    name="px_control_server",
                )
                main_app_process.start()
                websocket_app_process.start()
                reload_handler.restart_pending = False

            app_directory = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "app"
            )

            ignore_patterns = ['*.log', 'tmp/*', ".venv", ".pyc", "temp.py"]
            reload_handler = ReloadHandler(
                restart_app, ignore_patterns=ignore_patterns, debounce_duration=2
            )
            observer = Observer()
            observer.schedule(
                reload_handler,
                path=app_directory,
                recursive=True,
                event_filter=[
                    FileMovedEvent,
                    FileModifiedEvent,
                    FileCreatedEvent,
                ],
            )
            observer.start()
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
        terminate_processes([websocket_app_process, main_app_process])


if __name__ == '__main__':
    main()
