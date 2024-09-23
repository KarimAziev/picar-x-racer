import argparse
import os

import uvicorn

from app.util.logger import Logger

os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio"

logger = Logger(__name__)


if __name__ == "__main__":
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
        default="9000",
        help="The port to run the application on",
    )

    args = parser.parse_args()
    port = args.port
    print(f"starting args {args}")
    log_level = "DEBUG" if args.debug else args.log_level or "INFO"
    reload = args.reload if args.reload else False
    log_level = log_level.upper()
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_log_levels:
        print(f"Invalid log level: {log_level}. Using DEBUG.")
        log_level = "DEBUG"

    log_level_constant = getattr(Logger, log_level, Logger.DEBUG)

    Logger.set_global_log_level(log_level_constant)

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
