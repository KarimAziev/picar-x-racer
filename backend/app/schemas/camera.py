from typing import List, Optional, Union

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated


class PhotoResponse(BaseModel):
    """
    A response object containing the filename of the captured photo.
    """

    file: str = Field(
        ...,
        description="The the filename of the captured photo.",
        examples=["photo_2024-12-04-17-35-36.jpg"],
    )


class CameraSettings(BaseModel):
    """
    Model representing camera settings and configurations.

    Validators:
    --------------
    - Ensures both `width` and `height` must either be specified together or not at all.
    """

    device: Annotated[
        Optional[str],
        Field(
            None,
            title="Device",
            description="The path of the camera device.",
            examples=["/dev/video0", "/dev/video1"],
        ),
    ] = None
    width: Annotated[
        Optional[int],
        Field(
            ...,
            title="Frame Width",
            description="The width of the camera frame in pixels.",
            examples=[320, 640, 800, 1024, 1280],
        ),
    ] = None
    height: Annotated[
        Optional[int],
        Field(
            ...,
            title="Frame Height",
            description="The height of the camera frame in pixels.",
            examples=[180, 480, 600, 768, 720],
        ),
    ] = None
    fps: Annotated[
        Optional[float],
        Field(
            ...,
            title="Frames Per Second",
            description="The number of frames per second the camera should capture.",
            examples=[30, 15, 20],
        ),
    ] = None
    pixel_format: Annotated[
        Optional[str],
        Field(
            ...,
            title="Pixel Format",
            description="The format for the pixels (e.g., 'RGB', 'GRAY').",
            examples=[
                "YU12",
                "YUYV",
                "RGB3",
                "JPEG",
                "H264",
                "MJPG",
                "YVYU",
                "VYUY",
                "UYVY",
                "NV12",
                "BGR3",
                "YV12",
                "NV21",
                "RX24",
                "RGB",
                "GRAY",
                "BGR",
            ],
        ),
    ] = None

    media_type: Annotated[
        Optional[str],
        Field(
            ...,
            title="Media Type",
            description="The media type. Will be used if GStreamer is installed "
            "and opencv-python is compiled with GStreamer support.",
            examples=[
                "video/x-raw",
                "video/x-h264",
                "image/jpeg",
            ],
        ),
    ] = None
    use_gstreamer: Annotated[
        Optional[bool],
        Field(
            ...,
            description="Whether to use GStreamer for streaming. "
            "This setting should be enabled only if GStreamer is "
            "installed and opencv-python is compiled with GStreamer support.",
            examples=[True, False],
        ),
    ] = False

    @model_validator(mode="after")
    def validate_dimensions(cls, values):
        width = values.width
        height = values.height
        if (width is not None and height is None) or (
            width is None and height is not None
        ):
            raise ValueError("Both 'width' and 'height' must be specified together.")
        return values


class DeviceItem(BaseModel):
    """
    A model representing a camera device item, which serves as a base for other device-related models.
    """

    name: Optional[str] = Field(
        None,
        description="A human-readable label for the camera device, "
        "including its device path and additional information such as the model or manufacturer.",
        examples=["(Integrated Camera: Integrated C)"],
    )


class DeviceCommonProps(BaseModel):
    """
    Model representing common properties shared by camera devices.
    """

    device: str = Field(
        ...,
        description="The device path of the camera the mode is associated with.",
        examples=["/dev/video0"],
    )
    pixel_format: Optional[str] = Field(
        None,
        description="The pixel format used by the camera mode, such as MJPG or YUYV.",
        examples=[
            "MJPG",
            "YUYV",
            "YU12",
            "YUYV",
            "RGB3",
            "JPEG",
            "RGB3",
            "H264",
            "YVYU",
            "VYUY",
            "UYVY",
            "NV12",
            "BGR3",
            "YV12",
            "NV21",
            "RX24",
        ],
    )
    media_type: Annotated[
        Optional[str],
        Field(
            ...,
            title="Media Type",
            description="The media type. Will be used if GStreamer is installed "
            "and opencv-python is compiled with GStreamer support.",
            examples=[
                "video/x-raw",
                "video/x-h264",
                "image/jpeg",
            ],
        ),
    ] = None

    api: Annotated[
        Optional[str],
        Field(
            None,
            title="Device API",
            description="The API used to interface with the device.",
            examples=[
                "libcamera",
                "v4l2",
            ],
        ),
    ]
    path: Annotated[
        Optional[str],
        Field(
            ...,
            title="Device path",
            description="The device path without api prefix.",
            examples=[
                "/base/soc/i2c0mux/i2c@1/imx708@1a",
                "/dev/video21",
            ],
        ),
    ] = None


class DiscreteDevice(DeviceItem, DeviceCommonProps):
    """
    A model representing a discrete camera device configuration, including
    resolution, frame rate, and pixel format.
    """

    width: int = Field(
        ...,
        title="Frame Width",
        description="The width of the camera frame in pixels.",
        examples=[320, 640, 800, 1024, 1280],
    )
    height: int = Field(
        ...,
        title="Frame Height",
        description="The height of the camera frame in pixels.",
        examples=[180, 480, 600, 768, 720],
    )
    fps: Optional[float] = Field(
        None,
        description="The frame rate of the camera mode, measured in frames per second (fps).",
        examples=[10, 20, 30],
    )


class DeviceStepwiseBase(DeviceItem, DeviceCommonProps):
    """
    A model representing a stepwise configuration for a device with adjustable
    properties such as resolution, frame rate, and pixel format.
    """

    min_width: int = Field(
        ...,
        title="Minimum Frame Width",
        description="The minimum width of the camera frame in pixels.",
        examples=[320, 640],
    )
    max_width: int = Field(
        ...,
        title="Maximum Frame Width",
        description="The maximum width of the camera frame in pixels.",
        examples=[1280, 1920],
    )
    min_height: int = Field(
        ...,
        title="Minimum Frame Height",
        description="The minimum height of the camera frame in pixels.",
        examples=[180, 480],
    )
    max_height: int = Field(
        ...,
        title="Maximum Frame Height",
        description="The maximum height of the camera frame in pixels.",
        examples=[720, 1080],
    )
    height_step: int = Field(
        ...,
        title="Height Step Size",
        description="The step size in pixels for adjusting frame height.",
        examples=[1, 2, 10],
    )
    width_step: int = Field(
        ...,
        title="Width Step Size",
        description="The step size in pixels for adjusting frame width.",
        examples=[1, 2, 10],
    )


class DeviceStepwise(DeviceStepwiseBase):
    """
    A model representing a stepwise configuration for a device with adjustable
    properties such as resolution, frame rate, and pixel format.
    """

    min_fps: float = Field(
        ...,
        description="The minimal frame rate of the camera mode, measured in frames per second (fps).",
        examples=[1, 20, 30],
    )

    max_fps: float = Field(
        ...,
        description="The maximum frame rate of the camera mode, measured in frames per second (fps).",
        examples=[90],
    )


class CameraDevicesResponse(BaseModel):
    """
    Successful response for available camera devices.
    """

    devices: List[
        Union[
            DeviceStepwise,
            DiscreteDevice,
        ]
    ] = Field(
        ...,
        description=("A list of camera devices and their configurations."),
        examples=[
            [
                {
                    "device": "/dev/video0",
                    "pixel_format": "MJPG",
                    "label": "MJPG, 640x360, 30 fps",
                    "width": 640,
                    "height": 360,
                    "fps": 30,
                },
                {
                    "device": "/dev/video1",
                    "pixel_format": "YU12",
                    "min_width": 32,
                    "max_width": 2592,
                    "min_height": 32,
                    "max_height": 1944,
                    "height_step": 2,
                    "width_step": 2,
                    "min_fps": 1,
                    "max_fps": 90,
                },
                {
                    "device": "/dev/video1",
                    "pixel_format": "YUYV",
                    "min_width": 32,
                    "max_width": 2592,
                    "min_height": 32,
                    "max_height": 1944,
                    "height_step": 2,
                    "width_step": 2,
                    "min_fps": 1,
                    "max_fps": 90,
                },
            ]
        ],
    )
