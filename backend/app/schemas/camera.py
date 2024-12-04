from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class PhotoResponse(BaseModel):
    """
    A response object containing the filename of the captured photo
    """

    file: str


class CameraSettings(BaseModel):
    """
    Model representing camera settings and configurations.

    Attributes:
    --------------
    - `device` (Optional[str]): ID or name of the camera device.
    - `width` (Optional[int]): Frame width in pixels.
    - `height` (Optional[int]): Frame height in pixels.
    - `fps` (Optional[int]): Frames per second for capturing.
    - `pixel_format` (Optional[str]): Pixel format, such as 'RGB' or 'GRAY'.

    Validators:
    --------------
    - Ensures both `width` and `height` must either be specified together or not at all.
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
    """
    Response model for available camera devices.

    Attributes:
    --------------
    - `devices` (List[Dict[str, Union[str, bool, List[Dict[str, str]]]]]):
      A list of devices with details such as paths, categories, and supported formats.

    Example:
    --------------
    ```json
    {
        "devices": [
            {
                "key": "/dev/video0",
                "label": "/dev/video0 (Primary Camera)",
                "selectable": False,
                "children": [
                    {"key": "MJPEG", "label": "MJPEG (1920x1080)"},
                    {"key": "YUYV", "label": "YUYV (640x480)"}
                ]
            },
            {
                "key": "/dev/video1",
                "label": "/dev/video1 (Secondary Camera)",
                "selectable": False,
                "children": [
                    {"key": "H264", "label": "H264 (1280x720)"}
                ]
            }
        ]
    }
    ```
    """

    devices: List[Dict[str, Union[str, bool, List[Dict[str, str]]]]]
