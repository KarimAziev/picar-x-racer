import logging.config
import os

level = os.getenv("LOG_LEVEL", "INFO").upper()


class ExcludeBinaryFilter(logging.Filter):
    def filter(self, record):
        return "> BINARY " not in record.getMessage()


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
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console_color_ext"],
            "level": level,
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console_color_ext"],
            "level": level,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console_color_ext"],
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
