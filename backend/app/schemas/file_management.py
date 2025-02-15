from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated


class MediaType(str, Enum):
    """Enumeration of supported file operations scoped by type."""

    video = "video"
    image = "image"
    music = "music"
    data = "data"


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
        ...,
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

    media_type: MediaType = Field(
        ...,
        description="The media type of the file.",
        examples=[
            MediaType.video.value,
            MediaType.image.value,
            MediaType.music.value,
            MediaType.data.value,
        ],
    )
    archive_name: Annotated[
        str,
        Field(
            ...,
            description="The archive file name.",
        ),
    ] = ""

    @model_validator(mode="after")
    def validate_archive_name(self):
        if not isinstance(self.archive_name, str) or not self.archive_name.strip():
            media_type = self.media_type
            if media_type:
                self.archive_name = f"{media_type}_files_archive.zip"
            else:
                raise ValueError(
                    "media_type must be provided if archive_name is missing"
                )

        if not self.archive_name.lower().endswith(".zip"):
            self.archive_name = f"{self.archive_name}.zip"

        return self


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


class VideoDetail(BaseModel):
    """
    A model to represent a video filename's metadata.
    """

    track: str = Field(
        ...,
        description="The name of the video file without directory, but with extension",
        examples=["recording_2024-12-12-17-42-05.avi"],
    )
    preview: Optional[str] = Field(
        ...,
        description="The name of the generated preview image without directory, but with extension",
        examples=["recording_2024-12-12-17-42-05_1734018196.jpg"],
    )
    duration: float = Field(
        ...,
        description="The name of the generated preview iamge without directory, but with extension",
        examples=[25.7, 2.733333],
    )
