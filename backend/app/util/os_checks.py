import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache()
def is_raspberry_pi() -> bool:
    """
    Check if the current operating system is running on a Raspberry Pi.

    Returns:
        bool: True if the OS is running on a Raspberry Pi, False otherwise.
    """
    try:
        with open("/proc/device-tree/model", "r") as file:
            model_info = file.read().lower()
        return "raspberry pi" in model_info
    except FileNotFoundError:
        return False


@lru_cache()
def get_gpio_factory_name() -> str:
    """
    Determines the appropriate GPIO factory name based on the Raspberry Pi model.

    This function reads the device-tree model information from the system.
    - If the model indicates a Raspberry Pi 5, it returns "lgpio".
    - If the model indicates any other Raspberry Pi, it returns "rpigpio".
    - In case of any error or if the model file is missing, it returns "mock".

    Returns:
        The GPIO factory name to use.
    """
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                model_bytes = f.read()
                model_str = model_bytes.decode("utf-8").strip("\x00").lower()
                if "raspberry pi 5" in model_str:
                    return "lgpio"
                elif "raspberry pi" in model_str:
                    return "rpigpio"
        except Exception as e:
            logger.error("Error reading model file: %s", e)
            return "mock"
    return "mock"
