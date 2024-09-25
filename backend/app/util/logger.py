import logging
import os
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

    _handlers_added_pids = set()
    _app_logger_name = "picar-x-racer"

    def __init__(
        self,
        name: str,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        log_colors: Optional[Dict[str, str]] = None,
    ):
        if hasattr(self, "logger"):
            return

        if not name.startswith(self._app_logger_name):
            full_name = f"{self._app_logger_name}.{name}"
        else:
            full_name = name

        self.logger = logging.getLogger(full_name)

        self.logger.propagate = True

        current_pid = os.getpid()
        if current_pid not in Logger._handlers_added_pids:
            self._add_app_handlers(fmt, datefmt, log_colors)
            Logger._handlers_added_pids.add(current_pid)

    @classmethod
    def _add_app_handlers(cls, fmt, datefmt, log_colors):
        app_logger = logging.getLogger(cls._app_logger_name)

        if app_logger.handlers:
            app_logger.handlers = []

        fmt = (
            fmt
            or "%(log_color)s%(asctime)s [%(process)d] - %(name)s - %(levelname)s - %(message)s"
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
        app_logger.addHandler(console_handler)

        app_logger.setLevel(logging.INFO)

    def set_level(self, level: int):
        if level not in self.LEVELS.values():
            raise ValueError(f"Invalid log level: {level}")

        self.logger.setLevel(level)

    @classmethod
    def set_global_log_level(cls, level: int):
        if level not in cls.LEVELS.values():
            raise ValueError(f"Invalid log level: {level}")

        app_logger = logging.getLogger(cls._app_logger_name)
        app_logger.setLevel(level)

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

        app_logger = logging.getLogger(self._app_logger_name)
        app_logger.addHandler(file_handler)

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
    def log_exception(message: str, exc: Exception):
        logging.error(f"{message}: {exc}")
