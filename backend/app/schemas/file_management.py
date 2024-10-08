from typing import List

from pydantic import BaseModel


class FilesResponse(BaseModel):
    """
    A model to represent a response containing a list of files.

    Attributes:
    - `files` (List[str]): A list of file names.
    """

    files: List[str]


class UploadFileResponse(BaseModel):
    """
    A model to represent a response after uploading a file.

    Attributes:
    - `success` (bool): Indicator of whether the upload was successful.
    - `filename` (str): The name of the uploaded file.
    """

    success: bool
    filename: str


class RemoveFileResponse(BaseModel):
    """
    A model to represent a response after removing a file.

    Attributes:
    - `success` (bool): Indicator of whether the removal was successful.
    - `filename` (str): The name of the removed file.
    """

    success: bool
    filename: str
