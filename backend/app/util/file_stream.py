import os
from typing import Dict, Generator, Optional

from app.core.logger import Logger
from app.util.mime_type_helper import guess_mime_type
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

_log = Logger(__name__)


def stream_file_response(
    file_path: str,
    media_types: Dict[str, str],
    range_header: Optional[str] = None,
    chunk_size: int = 1024 * 1024,
) -> StreamingResponse:
    """
    Generic helper to return a StreamingResponse for a given file,
    supporting byte-range requests.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    file_size = os.path.getsize(file_path)
    file_extension = file_path.split(".")[-1].lower()
    guessed_mime_type = guess_mime_type(file_path)
    content_type = guessed_mime_type or media_types.get(
        file_extension, list(media_types.values())[0]
    )
    _log.debug("file_extension='%s', content_type='%s'", file_extension, content_type)

    def file_generator(start: int, end: int) -> Generator[bytes, None, None]:
        with open(file_path, "rb") as file:
            file.seek(start)
            current = start
            while current < end:
                data = file.read(min(chunk_size, end - current))
                if not data:
                    break
                yield data
                current += len(data)

    if range_header:
        try:
            range_val = range_header.replace("bytes=", "")
            parts = range_val.split("-")
            range_start = int(parts[0]) if parts[0] else 0
            range_end = int(parts[1]) if parts[1] else file_size - 1
        except (ValueError, IndexError):
            raise HTTPException(status_code=416, detail="Invalid byte range")
        if range_start >= file_size or range_end >= file_size:
            raise HTTPException(status_code=416, detail="Invalid byte range")
        content_length = range_end - range_start + 1
        headers = {
            "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": content_type,
        }
        return StreamingResponse(
            file_generator(range_start, range_end + 1),
            status_code=206,
            headers=headers,
            media_type=content_type,
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": content_type,
    }
    return StreamingResponse(
        file_generator(0, file_size),
        headers=headers,
        media_type=content_type,
    )
