import logging.config
import os

level = os.getenv("PX_LOG_LEVEL", "INFO").upper()


class ExcludeBinaryFilter(logging.Filter):
    def filter(self, record):
        return "> BINARY " not in record.getMessage()


class UvicornFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, use_colors=None):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record):
        record.name = ""
        if self.use_colors and record.levelno == logging.INFO:
            record.msg = f"\033[92m{record.msg}\033[0m"
        return super().format(record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "exclude_binary": {
            "()": ExcludeBinaryFilter,
        }
    },
    "formatters": {
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s%(asctime)s [PID %(process)d] - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%H:%M:%S",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        },
        "uvicorn": {
            "()": UvicornFormatter,
            "format": "s%(asctime)s [PID %(process)d] - uvicorn - %(levelname)s - %(message)s",
            "datefmt": "%H:%M:%S",
            "use_colors": True,
        },
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "colored_px": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s%(asctime)s [PID %(process)d] - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%H:%M:%S",
            "log_colors": {
                "DEBUG": "light_purple",
                "INFO": "light_green",
                "WARNING": "bold_yellow",
                "ERROR": "light_red",
                "CRITICAL": "red,bg_white",
            },
        },
        "colored_ext": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%H:%M:%S",
            "log_colors": {
                "DEBUG": "thin_purple",
                "INFO": "thin_green",
                "WARNING": "thin_yellow",
                "ERROR": "thin_red",
                "CRITICAL": "thin_red",
            },
        },
    },
    "handlers": {
        "console_colored": {
            "class": "logging.StreamHandler",
            "formatter": "colored",
            "filters": ["exclude_binary"],
        },
        "console_colored_px": {
            "class": "logging.StreamHandler",
            "formatter": "colored_px",
            "filters": ["exclude_binary"],
        },
        "console_color_ext": {
            "class": "logging.StreamHandler",
            "formatter": "colored_ext",
            "filters": ["exclude_binary"],
        },
        "console_default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["exclude_binary"],
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "default",
            "filters": ["exclude_binary"],
            "level": level,
        },
        "uvicorn": {
            "formatter": "uvicorn",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "filters": ["exclude_binary"],
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
        "picar-x-racer": {
            "handlers": ["console_colored_px"],
            "level": level,
            "propagate": False,
        },
        "px-control": {
            "handlers": ["console_colored"],
            "level": level,
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console_default"],
        "level": level,
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
