from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class UploadFileResponse(BaseModel):
    """
    A model to represent a response after uploading a file.
    """

    success: bool = Field(
        ...,
        description="Indicator of whether the upload was successful",
        examples=[True, False],
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

    success: bool = Field(
        ...,
        description="Indicator of whether the file was removed",
        examples=[True, False],
    )
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


class BatchFilesRequest(BaseModel):
    """
    A model to represent a request body for operations on multiple files.
    """

    filenames: List[str] = Field(
        None,
        description="The list of the filenames without directory, but with extension",
        examples=[["photo_2024-12-04-17-35-36.jpg", "photo_2024-12-04-17-35-33.jpg"]],
    )


class BatchRemoveFilesRequest(BatchFilesRequest):
    """
    A model to represent a request body for removing multiple files.
    """

    pass


class DownloadArchiveRequestPayload(BatchFilesRequest):
    """
    A model to represent a request data for downloading multiple files as an archive.
    """

    media_type: Literal["music", "image", "video", "data"] = Field(
        ...,
        description="The media type of the file.",
        examples=["image", "music" "video", "data"],
    )


class PhotoItem(BaseModel):
    """
    A model to represent a response containing a user photo.
    """

    name: str = Field(
        ...,
        description="The name of the filename without directory, but with extension",
        examples=["photo_2024-12-04-17-35-36.jpg"],
    )
    path: str = Field(
        ...,
        description="Full path of the file",
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
    """

    files: List[PhotoItem] = Field(
        ...,
        description="The list of objects with metadata",
    )
