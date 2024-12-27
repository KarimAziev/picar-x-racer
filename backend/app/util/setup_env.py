import argparse
import os

from app.util.os_checks import is_raspberry_pi


def setup_env():
    is_os_raspberry = is_raspberry_pi()

    os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio" if is_os_raspberry else "mock"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    if not is_os_raspberry:
        os.environ["ROBOT_HAT_MOCK_SMBUS"] = "1"
        os.environ["ROBOT_HAT_DISCHARGE_RATE"] = "10"

    parser = argparse.ArgumentParser(description="Run the application.")

    group = parser.add_mutually_exclusive_group()
    uvicorn_group = parser.add_argument_group(title="uvicorn")

    group.add_argument(
        "--debug", action="store_true", help="Set logging level to DEBUG."
    )

    group.add_argument(
        "--log-level",
        default=os.getenv("PX_LOG_LEVEL", "INFO"),
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    uvicorn_group.add_argument(
        "--dev", action="store_true", help="Start in development mode."
    )
    uvicorn_group.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PX_MAIN_APP_PORT", "8000")),
        help="The port to run the application on",
    )

    uvicorn_group.add_argument(
        "--px-port",
        type=int,
        default=int(os.getenv("PX_CONTROL_APP_PORT", "8001")),
        help="The port to run the Picar X Racer control websocket application on.",
    )

    uvicorn_group.add_argument(
        "--frontend-port",
        type=int,
        default=4000,
        help="The port to run the Picar X Racer frontend in dev mode.",
    )

    args = parser.parse_args()
    px_control_app_port: str = str(args.px_port)
    px_main_app_port: str = str(args.port)
    px_frontend_port: str = str(args.frontend_port)
    log_level = "DEBUG" if args.debug else args.log_level or "INFO"

    mode = "dev" if args.dev else "prod"
    log_level = log_level.upper()
    os.environ["PX_LOG_LEVEL"] = log_level
    os.environ["PX_CONTROL_APP_PORT"] = px_control_app_port
    os.environ["PX_MAIN_APP_PORT"] = px_main_app_port
    os.environ["PX_APP_MODE"] = mode
    return (px_main_app_port, px_control_app_port, log_level, mode, px_frontend_port)
