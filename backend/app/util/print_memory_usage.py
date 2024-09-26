import psutil
from app.util.logger import Logger

logger = Logger(__name__)


def print_memory_usage(description: str):
    memory = psutil.virtual_memory()
    logger.info(description)
    logger.info(f"System RAM - Total: {memory.total / (1024**3):.2f} GB")
    logger.info(f"System RAM - Used: {memory.used / (1024**3):.2f} GB")
    logger.info(f"System RAM - Available: {memory.available / (1024**3):.2f} GB")
    logger.info(f"System RAM - Usage Percentage: {memory.percent}%")
