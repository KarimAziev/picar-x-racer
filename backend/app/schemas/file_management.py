from typing import List

from pydantic import BaseModel


class FilesResponse(BaseModel):
    files: List[str]


class UploadFileResponse(BaseModel):
    success: bool
    filename: str


class RemoveFileResponse(BaseModel):
    success: bool
    filename: str
