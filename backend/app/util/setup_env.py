import argparse
import os
from typing import Literal, NamedTuple

from app.util.os_checks import get_gpio_factory_name, is_raspberry_pi

APP_MODE = Literal["dev", "prod"]


class AppEnvironment(NamedTuple):
    main_app_port: str
    control_app_port: str
    log_level: str
    mode: APP_MODE
    frontend_port: str


def setup_env_vars() -> bool:
    """
    Set up environment variables related to GPIO and platform detection.
    Returns True if running on a real Raspberry Pi, False otherwise.
    """
    if os.getenv("GPIOZERO_PIN_FACTORY") is None:
        gpio_factory_name = get_gpio_factory_name()
        os.environ["GPIOZERO_PIN_FACTORY"] = gpio_factory_name
        is_real_raspberry = gpio_factory_name != "mock"
    else:
        is_real_raspberry = is_raspberry_pi()

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    if not is_real_raspberry:
        for key, value in [
            ("ROBOT_HAT_MOCK_SMBUS", "1"),
            ("ROBOT_HAT_DISCHARGE_RATE", "10"),
        ]:
            os.environ.setdefault(key, value)

    return is_real_raspberry


def parse_cli_args() -> argparse.Namespace:
    """
    Parse command-line arguments and configure uvicorn settings.
    """
    parser = argparse.ArgumentParser(description="Run the application.")
    group = parser.add_mutually_exclusive_group()
    uvicorn_group = parser.add_argument_group(title="uvicorn")

    group.add_argument(
        "--debug", action="store_true", help="Set logging level to DEBUG."
    )
    group.add_argument(
        "--log-level",
        default=os.environ.get("PX_LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level.",
    )

    uvicorn_group.add_argument(
        "--dev", action="store_true", help="Start in development mode."
    )
    uvicorn_group.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PX_MAIN_APP_PORT", "8000")),
        help="Port to run the main application on.",
    )
    uvicorn_group.add_argument(
        "--px-port",
        type=int,
        default=int(os.environ.get("PX_CONTROL_APP_PORT", "8001")),
        help="Port for the Picar X Racer control websocket.",
    )
    uvicorn_group.add_argument(
        "--frontend-port",
        type=int,
        default=4000,
        help="Port for the frontend in dev mode.",
    )

    return parser.parse_args()


def setup_env() -> AppEnvironment:
    """
    Configure the runtime environment and parse command-line arguments.

    This function performs the following actions:
      1. Configures GPIO and related simulation variables.
      2. Hides the Pygame support prompt.
      3. Parses command-line arguments for logging and server configuration.
      4. Updates relevant environment variables.

    Returns:
        An AppEnvironment NamedTuple containing:
            - main_app_port: Port for the main application as string.
            - control_app_port: Port for the control app as string.
            - log_level: Logging level in uppercase.
            - mode: Application mode ('dev' if --dev is used, otherwise 'prod').
            - frontend_port: Port for the frontend as string.
    """
    setup_env_vars()
    args = parse_cli_args()

    main_app_port = str(args.port)
    control_app_port = str(args.px_port)
    frontend_port = str(args.frontend_port)
    log_level = "DEBUG" if args.debug else args.log_level
    mode: APP_MODE = "dev" if args.dev else "prod"

    log_level = log_level.upper()
    os.environ["PX_LOG_LEVEL"] = log_level
    os.environ["PX_CONTROL_APP_PORT"] = control_app_port
    os.environ["PX_MAIN_APP_PORT"] = main_app_port
    os.environ["PX_APP_MODE"] = mode

    return AppEnvironment(
        main_app_port, control_app_port, log_level, mode, frontend_port
    )
