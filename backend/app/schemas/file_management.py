from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated


class MediaType(str, Enum):
    """
    Directory alias for application content.

    This enumeration maps media type labels to their corresponding directory names used
    for storing various content (such as video, image, music, or miscellaneous data).
    Filenames in other models are always specified relative to the associated media type directory.
    """

    video = "video"
    image = "image"
    music = "music"
    data = "data"


class UploadFileResponse(BaseModel):
    """
    Response model returned after a file upload.
    """

    success: bool = Field(
        ...,
        description="A boolean flag indicating whether the file upload was successful.",
        examples=[True, False],
    )
    filename: str = Field(
        ...,
        description="The name of the uploaded file (relative to the media type directory). Example: 'my-song.mp3'.",
        examples=["my-song.mp3"],
    )


class BatchFileResult(BaseModel):
    """
    Result model for a single file operation in a batch process (e.g. removal or movement).
    """

    success: bool = Field(
        ...,
        description="A boolean flag indicating whether the file operation was successful.",
        examples=[True, False],
    )
    filename: str = Field(
        ...,
        description="The filename (relative to its media type directory) that was processed.",
        examples=["photo_2024-12-04-17-35-36.jpg"],
    )
    error: Optional[str] = Field(
        None,
        description="An error message if there was an issue processing the file.",
        examples=["Not found"],
    )


class BatchFilesRequest(BaseModel):
    """
    Request model for performing an operation on multiple files.
    """

    filenames: List[str] = Field(
        ...,
        description="A list of filenames (with extensions), each relative to its media type directory.",
        examples=[["photo_2024-12-04-17-35-36.jpg", "photo_2024-12-04-17-35-33.jpg"]],
    )


class BatchFilesMoveRequest(BatchFilesRequest):
    """
    Request model for moving multiple files to a new directory.
    """

    dir: str = Field(
        ...,
        description="The target directory alias where the files will be moved.",
        examples=["my_dir"],
    )


class BatchRemoveFilesRequest(BatchFilesRequest):
    """
    Request model for removing multiple files.
    """

    pass


class MakeDirRequest(BaseModel):
    """
    Request model for creating a new directory.
    """

    filename: str = Field(
        ...,
        description="The name of the directory to create (relative to the media type directory).",
        examples=["my_dir"],
    )


class MakeDirResponse(MakeDirRequest):
    """
    Response model returned after attempting to create a new directory.
    """

    success: bool = Field(
        ...,
        description="A boolean flag indicating whether the directory was successfully created.",
        examples=[True, False],
    )


class RenameFileRequest(BaseModel):
    """
    Request model for renaming a file.
    """

    filename: str = Field(
        ...,
        description="The current name of the file (relative to the media type directory) to be renamed.",
        examples=["my_photo.jpg"],
    )
    new_name: str = Field(
        ...,
        description="The new filename to assign to the file (relative to the media type directory).",
        examples=["my_new_photo.jpg"],
    )


class RenameFileResponse(RenameFileRequest):
    """
    Response model returned after a file renaming operation.
    """

    success: bool = Field(
        ...,
        description="A boolean flag indicating whether the file was successfully renamed.",
        examples=[True, False],
    )
    error: Optional[str] = Field(
        None,
        description="An error message if the rename operation failed.",
        examples=["Not found"],
    )


class DownloadArchiveRequestPayload(BatchFilesRequest):
    """
    Request model for downloading multiple files as a ZIP archive.
    """

    media_type: MediaType = Field(
        ...,
        description="Specifies the media type (directory alias) of the files to archive.",
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
            description="The desired archive file name. If empty or invalid, a default name based on the media type is generated.",
        ),
    ] = ""

    @model_validator(mode="after")
    def validate_archive_name(self):
        if not isinstance(self.archive_name, str) or not self.archive_name.strip():
            if self.media_type:
                self.archive_name = f"{self.media_type}_files_archive.zip"
            else:
                raise ValueError(
                    "media_type must be provided if archive_name is missing"
                )
        if not self.archive_name.lower().endswith(".zip"):
            self.archive_name = f"{self.archive_name}.zip"
        return self


class SaveFileRequest(BaseModel):
    """
    Request model for saving or updating file content.
    """

    path: Annotated[
        str,
        Field(
            ...,
            description="The target file path (relative to its media type directory) where the content will be saved.",
        ),
    ]
    content: Annotated[
        str,
        Field(
            ...,
            description="The text content to write into the file.",
        ),
    ]
    dir: Annotated[
        Optional[str],
        Field(
            ...,
            description="Optional directory alias which, if provided, specifies the media type directory in which to save the file.",
            examples=["my_dir"],
        ),
    ] = None
