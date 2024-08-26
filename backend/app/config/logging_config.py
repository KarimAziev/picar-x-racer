import logging
from colorlog import ColoredFormatter


def setup_logger(name: str):
    """
    Sets up a logger with a ColoredFormatter.
    Args:
    - name (str): The name of the logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger
