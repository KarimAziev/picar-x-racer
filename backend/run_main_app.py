import argparse
import multiprocessing as mp
import os

import uvicorn


def start_main_app(port: int, log_level: str, reload: bool):
    from app.main_server import app

    app.state.port = port
    app_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "app")
    uvicorn_config = {
        "app": "app.main_server:app",
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


if __name__ == "__main__":
    from app.util.logger import Logger
    from app.util.print_memory_usage import print_memory_usage

    print_memory_usage("Memory before running app")
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass
    print_memory_usage("Memory after spawning method")
    from app.util.setup_env import setup_env

    setup_env()

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
    start_main_app(port=port, log_level=log_level, reload=reload)
