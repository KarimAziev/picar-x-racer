import os
from contextlib import contextmanager
from pathlib import Path
from typing import Union


@contextmanager
def atomic_write(file_name: Union[str, Path], mode: str = "w"):
    """
    Context manager for atomic writing to a file.

    Writes to a temporary file and renames it to the target file upon successful completion.
    Supports both text and binary writing modes.

    Args:
        file_name (Union[str, Path]): Target file name.
        mode (str): File mode. Use "w" for text (default) or "wb" for binary.

    Yields:
        A file-like object for writing.

    Raises:
        Exception: Propagates any exception raised during the writing process.
    """
    file_path = Path(file_name)
    temp_name = file_path.with_suffix(f"{file_path.suffix}.tmp")

    file_path.parent.mkdir(exist_ok=True, parents=True)

    try:
        with open(temp_name, mode) as tmp:
            yield tmp

        os.rename(temp_name, file_path)
    except Exception:
        if temp_name.exists():
            temp_name.unlink()
        raise
