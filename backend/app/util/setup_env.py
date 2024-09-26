import os

from app.util.os_checks import is_raspberry_pi


def setup_env():
    is_os_raspberry = is_raspberry_pi()

    os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio" if is_os_raspberry else "mock"
