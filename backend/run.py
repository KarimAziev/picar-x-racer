import multiprocessing as mp
import argparse
import os
import sys
import time

import uvicorn

from app.util.logger import Logger
from app.util.os_checks import is_raspberry_pi


def terminate_processes(processes):
    print("Terminating child processes...")
    for process in processes:
        process.terminate()
    for process in processes:
        process.join()
    print("Child processes terminated. Exiting.")
    sys.exit(0)


def start_main_app(port: int, log_level: str, reload: bool):
    app_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "app")
    uvicorn_config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "port": port,
        "log_level": log_level.lower(),
    }

    if reload:
        uvicorn_config.update(
            {
                "reload": reload,
                "reload_dirs": [app_directory],
                "reload_includes": ["*.py"],
                "reload_excludes": ["*.log", "tmp/*"],
            }
        )

    uvicorn.run(**uvicorn_config)


def start_websocket_app(ws_port: int, log_level: str, reload: bool):
    app_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "app")
    uvicorn_config = {
        "app": "app.websocket_app:app",
        "host": "0.0.0.0",
        "port": ws_port,
        "log_level": log_level.lower(),
    }

    if reload:
        uvicorn_config.update(
            {
                "reload": reload,
                "reload_includes": ["*.py"],
                "reload_dirs": [app_directory],
                "reload_excludes": ["*.log", "tmp/*"],
            }
        )

    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    try:
        mp.set_start_method("spawn", force=True)
        print("spawned")
    except RuntimeError:
        pass
    is_os_raspberry = is_raspberry_pi()

    os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio" if is_os_raspberry else "mock"

    from app.robot_hat.pin import Pin

    mcu_reset = Pin("MCURST")
    mcu_reset.off()
    time.sleep(0.01)
    mcu_reset.on()
    time.sleep(0.01)

    mcu_reset.close()

    parser = argparse.ArgumentParser(description="Run the application.")

    group = parser.add_mutually_exclusive_group()
    uvicorn_group = parser.add_argument_group(title="uvicorn")

    group.add_argument(
        "--debug", action="store_true", help="Set logging level to DEBUG."
    )
    group.add_argument(
        "--log-level",
        default="INFO",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    uvicorn_group.add_argument(
        "--reload", action="store_true", help="Enable auto-reloading of the server."
    )
    uvicorn_group.add_argument(
        "--port",
        type=int,
        default="8000",
        help="The port to run the application on",
    )

    uvicorn_group.add_argument(
        "--ws-port",
        type=int,
        default=8001,
        help="The port to run the WebSocket application on.",
    )

    args = parser.parse_args()
    ws_port = args.ws_port
    port = args.port
    log_level = "DEBUG" if args.debug else args.log_level or "INFO"
    reload = args.reload if args.reload else False
    log_level = log_level.upper()
    os.environ["LOG_LEVEL"] = log_level

    Logger.setup_from_env()
    main_app_process = mp.Process(target=start_main_app, args=(port, log_level, reload))
    websocket_app_process = mp.Process(
        target=start_websocket_app, args=(ws_port, log_level, reload)
    )

    processes = [main_app_process, websocket_app_process]

    try:
        main_app_process.start()
        websocket_app_process.start()

        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Initiating graceful shutdown...")
        terminate_processes(processes)
    except Exception as e:
        print(f"An error occurred: {e}")
        terminate_processes(processes)
