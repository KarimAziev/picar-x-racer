import os

from app.config.platform import is_os_raspberry


def setup_env():
    os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio" if is_os_raspberry else "mock"
