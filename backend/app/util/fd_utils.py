import os

from app.core.logger import Logger

logger = Logger(__name__)


from contextlib import contextmanager
from typing import Any, Generator, Optional


@contextmanager
def fd_open(device_path: str, flags: int) -> Generator[int, Any, None]:
    """
    Context manager to open a device file and ensure proper cleanup.

    Args:
        device_path: Path to the device (e.g., `/dev/video0`).
        flags: Flags to open the file (e.g., os.O_RDWR).

    Yields:
        int: File descriptor of the opened device.

    Raises:
        Exception: Propagates any exception raised during the process.
    """
    fd: Optional[int] = None
    try:
        fd = os.open(device_path, flags)
        yield fd
    finally:
        if fd is not None:
            os.close(fd)
