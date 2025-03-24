"""
Common responses for file management endpoints.
"""

from typing import Any, Dict, Union

ResponsesDict = Dict[Union[int, str], Dict[str, Any]]

alias_dir_validation_error_response: ResponsesDict = {
    422: {
        "description": "Unprocessable Entity.",
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "type": "enum",
                            "loc": ["path", "alias_dir"],
                            "msg": "Input should be 'video', 'image', 'music' or 'data'",
                            "input": "imageasfafaf",
                            "ctx": {"expected": "'video', 'image', 'music' or 'data'"},
                        }
                    ]
                }
            }
        },
    }
}


octet_stream_response: Dict[str, Any] = {
    "content": {
        "application/octet-stream": {
            "example": "This is binary content; the example is not directly usable for file downloads."
        }
    },
}


upload_responses: ResponsesDict = {
    400: {
        "description": "Bad Request. Invalid filename.",
        "content": {"application/json": {"example": {"detail": "Invalid filename."}}},
    },
    500: {
        "description": "Internal Server Error. An unexpected error occurred.",
        "content": {
            "application/json": {"example": {"detail": "Failed to upload the file"}}
        },
    },
}


remove_file_responses: ResponsesDict = {
    404: {
        "description": "Not Found. The file could not be found or resolved.",
        "content": {"application/json": {"example": {"detail": "File not found."}}},
    },
    500: {
        "description": "Internal Server Error. An unexpected error occurred.",
        "content": {
            "application/json": {
                "example": {"detail": "Failed to remove '/my_abs_file/my_file.wav'"}
            }
        },
    },
}


remove_file_responses_in_aliased_dir: ResponsesDict = {
    **remove_file_responses,
    500: {
        **remove_file_responses[500],
        "content": {
            "application/json": {
                "example": {"detail": "Failed to remove 'my_file.wav'"}
            }
        },
    },
}


download_file_responses: ResponsesDict = {
    200: {
        **octet_stream_response,
        "description": "A file is returned.",
    },
    404: {"description": "File not found."},
}


download_archive_responses: ResponsesDict = {
    200: {
        **octet_stream_response,
        "description": "An archive containing the requested files is returned.",
        "headers": {
            "Content-Disposition": {
                "description": "Specifies that the response content is an attachment.",
                "example": 'attachment; filename="music_files_archive.zip"',
            }
        },
    },
    404: {
        "description": "One or more files were not found.",
        "content": {
            "application/json": {
                "example": {"detail": "File not found: my_nonexistent_file"}
            }
        },
    },
    422: {
        "description": "Validation error.",
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "type": "literal_error",
                            "loc": ["body", "alias_dir"],
                            "msg": "Input should be 'music', 'image', 'video' or 'data'",
                            "input": "images",
                            "ctx": {"expected": "'music', 'image', 'video' or 'data'"},
                        }
                    ]
                }
            }
        },
    },
}


image_preview_responses: ResponsesDict = {
    200: {
        "content": {
            "image/jpeg": {
                "example": "Binary JPEG content; the example is not directly usable."
            },
            "image/png": {
                "example": "Binary PNG content; the example is not directly usable."
            },
        },
        "description": "A preview image is returned.",
    },
    404: {"description": "File not found."},
}


download_video_responses: ResponsesDict = {
    200: {
        **octet_stream_response,
        "description": "A video file is returned.",
    },
    404: {"description": "File not found."},
}

video_stream_responses: ResponsesDict = {
    200: {
        "content": {
            "video/mp4": {"example": "This is a streamed video response."},
            "video/x-msvideo": {"example": "This is a streamed video response."},
            "video/quicktime": {"example": "This is a streamed video response."},
            "video/x-matroska": {"example": "This is a streamed video response."},
        },
        "description": "A video file is streamed.",
    },
    206: {
        "content": {
            "video/mp4": {
                "example": "This is a streamed video response supporting partial content."
            },
            "video/x-msvideo": {
                "example": "This is a streamed video response with byte ranges."
            },
        },
        "description": "Partial content streaming for video.",
    },
    404: {"description": "File not found."},
    416: {"description": "Invalid byte range."},
}

write_file_responses: ResponsesDict = {
    400: {"description": "Bad Request: Error writing file."},
    500: {"description": "Internal Server Error: Error writing file."},
}

audio_stream_responses: ResponsesDict = {
    200: {
        "content": {
            "audio/mpeg": {"example": "This is a streamed audio response."},
            "audio/ogg": {"example": "This is a streamed audio response."},
            "audio/wav": {"example": "This is a streamed audio response."},
        },
        "description": "Audio file is streamed.",
    },
    206: {
        "content": {
            "audio/mpeg": {
                "example": "This is a streamed audio response supporting partial content."
            },
            "audio/ogg": {
                "example": "This is a streamed audio response with byte ranges."
            },
        },
        "description": "Partial content streaming for audio.",
    },
    404: {"description": "File not found."},
    416: {"description": "Invalid byte range."},
}
