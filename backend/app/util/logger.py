import logging
import os
from typing import Optional

from app.config.log_config import setup_logging


class Logger:
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
        app_name: Optional[str] = None,
    ):
        if app_name is not None:
            Logger._app_logger_name = app_name

        if not logging.root.handlers:
            setup_logging()

        full_name = (
            f"{self._app_logger_name}.{name}"
            if not name.startswith(self._app_logger_name)
            else name
        )
        self.logger = logging.getLogger(full_name)

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

    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self.logger.critical(message, *args, **kwargs)

    @staticmethod
    def setup_global(log_level: str):
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            log_level = "DEBUG"
        log_level_constant = getattr(Logger, log_level.upper(), Logger.DEBUG)
        Logger.set_global_log_level(log_level_constant)

    @staticmethod
    def setup_from_env():
        log_level = os.getenv("PX_LOG_LEVEL", "INFO").upper()
        Logger.setup_global(log_level)

    @staticmethod
    def log_exception(message: str, exc: Exception):
        logging.exception(message, exc_info=exc)
