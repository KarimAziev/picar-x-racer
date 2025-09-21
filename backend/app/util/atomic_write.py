import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Generator, Optional, Union

from app.core.logger import Logger

_log = Logger(__name__)


@contextmanager
def atomic_write(
    file_name: Union[str, Path], mode: str = "w", encoding: Optional[str] = None
) -> Generator[IO[Any], Any, None]:
    """
    Context manager for atomic writing to a file.

    Writes to a temporary file and renames it to the target file upon successful completion.
    Supports both text and binary writing modes.

    Args:
        `file_name`: Target file name. Either a string or a pathlib.Path object.
        `mode`: File mode. Use "w" for text (default) or "wb" for binary.
        `encoding`: Text encoding (used only in text mode).

    Yields:
        A file-like object for writing.

    Raises:
        Exception: Propagates any exception raised during the writing process.
    """

    file_path = Path(file_name)
    unique_suffix = uuid.uuid4().hex
    temp_name = file_path.with_name(f"{file_path.name}.{unique_suffix}.tmp")

    file_path.parent.mkdir(exist_ok=True, parents=True)

    _log.debug(
        "Writing to %s temporary file: %s (mode: %s, encoding: %s)",
        file_name,
        temp_name,
        mode,
        encoding,
    )

    try:
        with open(temp_name, mode=mode, encoding=encoding) as tmp:
            yield tmp

        _log.debug(
            "Successfully wrote to temporary file: %s; replacing original file: %s",
            temp_name,
            file_name,
        )

        temp_name.replace(file_path)
    except Exception as e:
        _log.error("Error writing to %s: %s", file_name, e)
        if temp_name.exists():
            temp_name.unlink()
        raise
