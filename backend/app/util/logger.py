import logging
from typing import Dict, Optional

from colorlog import ColoredFormatter


class Logger(object):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    LEVELS = {
        "debug": DEBUG,
        "info": INFO,
        "warning": WARNING,
        "error": ERROR,
        "critical": CRITICAL,
    }

    def __init__(
        self,
        name: str,
        level: int = DEBUG,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        log_colors: Optional[Dict[str, str]] = None,
    ):
        if hasattr(self, "logger"):
            return

        self.logger = logging.getLogger(name)
        self.logger.propagate = False

        if not self.logger.handlers:
            fmt = (
                fmt
                or "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            datefmt = datefmt or "%H:%M:%S"
            log_colors = log_colors or {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }

            formatter = ColoredFormatter(fmt, datefmt=datefmt, log_colors=log_colors)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        self.set_level(level)

    def set_level(self, level: int):
        valid_levels = [self.DEBUG, self.INFO, self.WARNING, self.ERROR, self.CRITICAL]
        if level not in valid_levels:
            raise ValueError(f"Invalid log level: {level}")
        self.logger.setLevel(level)

    def add_file_handler(
        self,
        file_path: str,
        level: int = DEBUG,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
    ):
        file_handler = logging.FileHandler(file_path)
        fmt = fmt or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
        file_formatter = logging.Formatter(fmt, datefmt=datefmt)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)
        self.logger.addHandler(file_handler)

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)

    @staticmethod
    def set_global_log_level(level: int):
        valid_levels = [
            Logger.DEBUG,
            Logger.INFO,
            Logger.WARNING,
            Logger.ERROR,
            Logger.CRITICAL,
        ]
        if level not in valid_levels:
            raise ValueError(f"Invalid log level: {level}")
        logging.getLogger().setLevel(level)

    @staticmethod
    def log_exception(message: str, exc: Exception):
        logging.error(f"{message}: {exc}")
