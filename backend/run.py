import argparse
import multiprocessing as mp
import os
import sys

from app.util.logger import Logger
from app.util.reset_mcu_sync import reset_mcu_sync
from app.util.setup_env import setup_env
from run_car_control_app import start_control_app
from run_frontend import start_frontend_app
from run_main_app import start_main_app


def terminate_processes(processes):
    print("Terminating child processes...")
    for process in processes:
        process.terminate()
    for process in processes:
        process.join()
    print("Child processes terminated. Exiting.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    setup_env()
    reset_mcu_sync()

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
        default=8000,
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
        target=start_control_app, args=(ws_port, log_level, reload)
    )

    processes = [main_app_process, websocket_app_process]

    if reload:
        frontend_dev_process = mp.Process(
            target=start_frontend_app, args=(port, ws_port)
        )
        processes.append(frontend_dev_process)

    try:
        for proc in processes:
            proc.start()

        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Initiating graceful shutdown...")
        terminate_processes(processes)
    except Exception as e:
        print(f"An error occurred: {e}")
        terminate_processes(processes)
