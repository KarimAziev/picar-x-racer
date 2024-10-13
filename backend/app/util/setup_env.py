import argparse
import os

from app.config.platform import is_os_raspberry


def setup_env():
    os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio" if is_os_raspberry else "mock"

    parser = argparse.ArgumentParser(description="Run the application.")

    group = parser.add_mutually_exclusive_group()
    uvicorn_group = parser.add_argument_group(title="uvicorn")

    group.add_argument(
        "--debug", action="store_true", help="Set logging level to DEBUG."
    )
    group.add_argument(
        "--frontend", action="store_true", help="Whether to start frontend in dev mode."
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
        "--px-port",
        type=int,
        default=8001,
        help="The port to run the Picar X Racer control websocket application on.",
    )

    args = parser.parse_args()
    px_control_app_port: str = str(args.px_port)
    px_main_app_port: str = str(args.port)
    log_level = "DEBUG" if args.debug else args.log_level or "INFO"
    mode = "dev" if args.reload else "prod"
    log_level = log_level.upper()
    os.environ["PX_LOG_LEVEL"] = log_level
    os.environ["PX_CONTROL_APP_PORT"] = px_control_app_port
    os.environ["PX_MAIN_APP_PORT"] = px_main_app_port
    os.environ["PX_APP_MODE"] = mode
    return (px_main_app_port, px_control_app_port, log_level, mode)
