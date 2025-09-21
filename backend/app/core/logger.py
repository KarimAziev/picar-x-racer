import logging
import os
from logging.config import dictConfig
from typing import Optional, Union


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
    _app_logger_name = "px"

    def __init__(
        self,
        name: str,
        app_name: Optional[str] = None,
    ) -> None:
        if app_name is not None:
            Logger._app_logger_name = app_name

        if not logging.root.handlers:
            self.setup_logging()

        full_name = (
            f"{self._app_logger_name}.{name}"
            if not name.startswith(self._app_logger_name)
            else name
        )
        self.logger = logging.getLogger(full_name)

    @staticmethod
    def setup_logging() -> None:
        """
        Configures a dictionary-based logging configuration based on the
        environment variables for log directory and level.

        - When a logging directory is provided in environmnent, logs are written to separate
        application and error log files, and messages at WARNING level or above
        are output to stdout.

        - When no logging directory is specified, all logs above the specified level
        are streamed to stdout.
        """
        from app.config.log_config import LogConfig

        log_config = LogConfig.make_log_config(
            log_dir=os.getenv("PX_LOG_DIR"),
            level=os.getenv("PX_LOG_LEVEL", "INFO").upper(),
        )

        dictConfig(log_config)

    def set_level(self, level: int) -> None:
        """Dynamically set log level for this logger (file handlers only)."""
        if level not in self.LEVELS.values():
            raise ValueError(f"Invalid log level: {level}")
        self.logger.setLevel(level)

    @classmethod
    def set_global_log_level(cls, level: int) -> None:
        """Dynamically adjust log levels for file-based handlers."""
        if level not in cls.LEVELS.values():
            raise ValueError(f"Invalid log level: {level}")
        app_logger = logging.getLogger(cls._app_logger_name)
        app_logger.setLevel(level)

    @staticmethod
    def setup_global(log_level: str) -> None:
        """Set the global log level dynamically (via string)."""
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_log_levels:
            log_level = "DEBUG"
        log_level_constant = getattr(Logger, log_level.upper(), Logger.DEBUG)
        Logger.set_global_log_level(log_level_constant)

    @staticmethod
    def setup_from_env() -> None:
        """Set global log level using PX_LOG_LEVEL from the environment."""
        log_level = os.getenv("PX_LOG_LEVEL", "INFO").upper()
        Logger.setup_global(log_level)

    def debug(self, message: str, *args, **kwargs) -> None:
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self.logger.warning(message, *args, **kwargs)

    def error(
        self,
        message: str,
        *args,
        exc_info: Optional[Union[bool, BaseException]] = None,
        **kwargs,
    ) -> None:
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        self.logger.exception(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        self.logger.critical(message, *args, **kwargs)

    @staticmethod
    def log_exception(message: str, exc: Optional[Exception] = None) -> None:
        if exc:
            logging.exception(message, exc_info=exc)
        else:
            logging.exception(message, exc_info=True)
