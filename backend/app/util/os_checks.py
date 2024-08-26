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
