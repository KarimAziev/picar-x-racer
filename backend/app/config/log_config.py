from pathlib import Path
from typing import Any, Dict, Optional

from app.util.file_util import resolve_absolute_path
from app.util.logger_filters import ExcludeBinaryAndAssetsFilter, RateLimitFilter
from app.util.uvicorn_log_formatter import UvicornFormatter


class LogConfig:
    """
    Utility class for managing logging configuration. It supports both file-based
    and console-based logging, with features such as colored log formatting, log
    filtering, and handling different logging levels.

    This class allows configuring various log handlers, formatters, and filters to
    enable proper management of logging output for applications such as Uvicorn servers.
    """

    LOG_COLORS = {
        "DEBUG": "bold_blue",
        "INFO": "bold_green",
        "WARNING": "bold_yellow",
        "ERROR": "bold_red",
        "CRITICAL": "bold_white,bg_red",
    }

    FILTERS = {
        "exclude_binary": {
            "()": ExcludeBinaryAndAssetsFilter,
        },
        "rate_limit": {
            "()": RateLimitFilter,
            "limit": 10,
        },
        "exclude_paths": {
            "()": "app.core.log_filters.ExcludePathFilter",
            "excluded_paths": ["Execute job: <picamera2.job.Job object"],
        },
    }

    @staticmethod
    def make_log_config(
        level: str,
        log_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sets up a dictionary-based logging configuration based on the log directory and level.

        - When a logging directory is provided, logs are written to separate
        application and error log files, and messages at WARNING level or above
        are output to stdout.

        - When no logging directory is specified, all logs above the specified level
        are streamed to stdout.

        Args:
        - level: The logging level to be applied (e.g., DEBUG, INFO, etc.).
        - log_dir: The directory where log files should be created. If None, logging will be stdout-only.

        Returns:
            A logging configuration dictionary compliant with `logging.config.dictConfig`.
        """

        log_dir = resolve_absolute_path(log_dir) if log_dir else None
        level = level
        app_log_filename: Optional[str] = None
        error_log_filename: Optional[str] = None
        if log_dir is None:
            dict_config = LogConfig.make_non_file_config(level)
        else:
            dir_path = Path(log_dir)
            dir_path.mkdir(parents=True, exist_ok=True)
            app_log_filename = dir_path.joinpath("app.log").as_posix()
            error_log_filename = dir_path.joinpath("error.log").as_posix()
            dict_config = LogConfig.make_file_config(
                app_log_file=app_log_filename,
                error_log_file=error_log_filename,
                level=level,
            )

        return dict_config

    @staticmethod
    def make_colored_formatter(handler_color: str) -> Dict[str, Any]:
        """
        Creates a configuration dictionary for a colored log formatter.

        This method generates a configuration for the `colorlog` package, allowing log messages to appear with colors
        based on their severity level. The color of the handler's name can also be customized.

        Args:
            handler_color: The color to apply for the handler's section in the log message.

        Returns:
            A dictionary representing the configuration of the colored formatter.
        """
        return {
            "()": "colorlog.ColoredFormatter",
            "format": f"%(asctime)s [PID %(process)d] - %({handler_color})s%(name)s%(reset)s - %(log_color)s%(levelname)s%(reset)s - %(reset)s%(message)s",
            "datefmt": "%H:%M:%S",
            "reset": True,
            "log_colors": LogConfig.LOG_COLORS,
        }

    @staticmethod
    def make_non_file_config(level: str) -> Dict[str, Any]:
        """
        Generates a logging configuration for a console-based (non-file) setup.

        This configuration is designed to send all log output to the console (stdout) without writing to any files.
        It supports multiple handlers, including colored output for different components.

        Args:
            level: The logging level to be applied (e.g., DEBUG, INFO, etc.).

        Returns:
            A dictionary representing the logging configuration for non-file-based logging.
        """
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": LogConfig.FILTERS,
            "formatters": {
                "uvicorn": {
                    "()": UvicornFormatter,
                    "format": "%(asctime)s [PID %(process)d] - uvicorn - %(levelname)s - %(message)s",
                    "datefmt": "%H:%M:%S",
                    "use_colors": True,
                },
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%H:%M:%S",
                },
                "main_server_colored": LogConfig.make_colored_formatter("blue"),
                "robot_colored": LogConfig.make_colored_formatter("green"),
                "robot_hat_colored": LogConfig.make_colored_formatter("purple"),
            },
            "handlers": {
                "px": {
                    "class": "logging.StreamHandler",
                    "formatter": "main_server_colored",
                },
                "robot_hat": {
                    "class": "logging.StreamHandler",
                    "formatter": "robot_hat_colored",
                },
                "robot_server": {
                    "class": "logging.StreamHandler",
                    "formatter": "robot_colored",
                },
                "console_default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
                "picamera2.picamera2": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["exclude_paths"],
                },
                "uvicorn": {
                    "formatter": "uvicorn",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "filters": ["exclude_binary", "rate_limit"],
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["uvicorn"],
                    "level": level,
                },
                "uvicorn.error": {
                    "handlers": ["uvicorn"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["uvicorn"],
                    "level": level,
                    "propagate": False,
                },
                "px": {
                    "handlers": ["px"],
                    "level": level,
                    "propagate": False,
                },
                "px_robot": {
                    "handlers": ["robot_server"],
                    "level": level,
                    "propagate": False,
                },
                "robot_hat": {
                    "handlers": ["robot_hat"],
                    "level": level,
                    "propagate": False,
                },
                "picamera2.picamera2": {
                    "handlers": ["picamera2.picamera2"],
                    "level": level,
                    "propagate": False,
                },
            },
            "root": {
                "handlers": ["console_default"],
                "level": level,
            },
        }

    @staticmethod
    def make_file_config(
        app_log_file: str, error_log_file: str, level: str
    ) -> Dict[str, Any]:
        """
        Sets up a file-based logging configuration.

        Logs are saved to rotating files for general application messages and error messages.
        Additionally, WARNING level logs or higher are also printed to the console. This setup
        is suitable for applications requiring structured log management with file rotation.

        Args:
            app_log_file: Path to the file that will store general application logs.
            error_log_file: Path to the file that will store error logs.
            level: The logging level to be applied (e.g., DEBUG, INFO, etc.).

        Returns:
            A dictionary representing the logging configuration compliant with `logging.config.dictConfig`.
        """
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": LogConfig.FILTERS,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                # Journaling (console) handler for systemd
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": "WARNING",
                },
                # General log file (rotating)
                "file_general": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": app_log_file,
                    "formatter": "default",
                    "level": level,
                    "maxBytes": 10_000_000,  # 10 MB per file
                    "backupCount": 5,  # Keep up to 5 backups (total: 50 MB max),
                    "filters": ["exclude_binary", "rate_limit"],
                },
                # Error log file (rotating)
                "file_error": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": error_log_file,
                    "formatter": "default",
                    "level": "ERROR",
                    "maxBytes": 10_000_000,  # 10 MB per file
                    "backupCount": 5,
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["console", "file_general", "file_error"],
                    "level": level,
                },
                "uvicorn.error": {
                    "handlers": ["console", "file_general", "file_error"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["console", "file_general", "file_error"],
                    "level": level,
                    "propagate": False,
                },
                "px": {
                    "handlers": ["console", "file_general", "file_error"],
                    "level": level,
                    "propagate": False,
                },
                "px_robot": {
                    "handlers": ["console", "file_general", "file_error"],
                    "level": level,
                    "propagate": False,
                },
                "robot_hat": {
                    "handlers": ["console", "file_general", "file_error"],
                    "level": level,
                    "propagate": False,
                },
            },
        }
