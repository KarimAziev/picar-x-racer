from typing import List, Optional

from pydantic import BaseModel, Field


class UploadFileResponse(BaseModel):
    """
    A model to represent a response after uploading a file.

    Attributes:
    - `success` (bool): Indicator of whether the upload was successful.
    - `filename` (str): The name of the uploaded file.
    """

    success: bool = Field(
        ..., description="Indicator of whether the upload was successful"
    )
    filename: str = Field(
        ...,
        description="The name of the uploaded file",
        examples=["my-song.mp3"],
    )


class RemoveFileResponse(BaseModel):
    """
    A model to represent a response after removing a file.
    """

    success: bool = Field(..., description="Indicator of whether the file was removed")
    filename: str = Field(
        ...,
        description="The name of the removed file",
        examples=["photo_2024-12-04-17-35-36.jpg"],
    )
    error: Optional[str] = Field(
        None,
        description="An error message if the file wasn't removed successfully",
        examples=["Not found"],
    )


class BatchRemoveFilesRequest(BaseModel):
    """
    A model to represent a request body for removing multiple files.
    """

    filenames: List[str] = Field(
        None,
        examples=["photo_2024-12-04-17-35-36.jpg"],
    )


class PhotoItem(BaseModel):
    """
    A model to represent a response containing a user photo.

    Attributes:
    - `name` (str): the name of the filename without directory, but with extension.
    - `path` (str): Full path of file.
    - `url` (str): Preview URL.
    """

    name: str = Field(
        ...,
        description="The name of the filename without directory, but with extension",
        examples=["photo_2024-12-04-17-35-36.jpg"],
    )
    path: str = Field(
        ...,
        description="Full path of file",
        examples=["/home/pi/Pictures/picar-x-racer/photo_2024-12-04-17-35-36.jpg"],
    )
    url: str = Field(
        ...,
        description="Preview URL",
        examples=["/api/files/preview/photo_2024-12-04-17-35-36.jpg"],
    )


class PhotosResponse(BaseModel):
    """
    A model to represent a response containing a list of user photos.

    Attributes:
    - `files` (PhotoItem[str]): A list of files.
    """

    files: List[PhotoItem]
