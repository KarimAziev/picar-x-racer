from typing import List

from pydantic import BaseModel


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


class PhotoItem(BaseModel):
    """
    A model to represent a response containing a user photo.

    Attributes:
    - `name` (str): the name of the filename without directory, but with extension.
    - `path` (str): Full path of file.
    - `url` (str): Preview URL.
    """

    name: str
    path: str
    url: str


class PhotosResponse(BaseModel):
    """
    A model to represent a response containing a list of user photos.

    Attributes:
    - `files` (PhotoItem[str]): A list of files.
    """

    files: List[PhotoItem]
