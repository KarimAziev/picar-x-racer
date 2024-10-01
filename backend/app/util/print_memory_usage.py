import psutil
from app.util.logger import Logger

logger = Logger(__name__)


def print_memory_usage(description: str):
    memory = psutil.virtual_memory()
    logger.debug(description)
    logger.debug(f"System RAM - Total: {memory.total / (1024**3):.2f} GB")
    logger.debug(f"System RAM - Used: {memory.used / (1024**3):.2f} GB")
    logger.debug(f"System RAM - Available: {memory.available / (1024**3):.2f} GB")
    logger.debug(f"System RAM - Usage Percentage: {memory.percent}%")
