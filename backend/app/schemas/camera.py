from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class PhotoResponse(BaseModel):
    """
    A response object containing the filename of the captured photo
    """

    file: str


class FrameDimensionsResponse(BaseModel):
    """
    A response object containing the width and height of the current camera frame.
    """

    width: int
    height: int


class CameraSettings(BaseModel):
    """
    A model to represent the camera device settings.
    """

    device: Optional[str] = Field(
        None, title="Device", description="The ID or name of the camera device."
    )
    width: Optional[int] = Field(
        None,
        title="Frame Width",
        description="The width of the camera frame in pixels.",
    )
    height: Optional[int] = Field(
        None,
        title="Frame Height",
        description="The height of the camera frame in pixels.",
    )
    fps: Optional[int] = Field(
        None,
        title="Frames Per Second",
        description="The number of frames per second the camera should capture.",
    )
    pixel_format: Optional[str] = Field(
        None,
        title="Pixel Format",
        description="The format for the pixels (e.g., 'RGB', 'GRAY').",
    )

    @model_validator(mode="after")
    def validate_dimensions(cls, values):
        width = values.width
        height = values.height
        if (width is not None and height is None) or (
            width is None and height is not None
        ):
            raise ValueError("Both 'width' and 'height' must be specified together.")
        return values


class CameraDevicesResponse(BaseModel):
    devices: List[Dict[str, Union[str, bool, List[Dict[str, str]]]]]
