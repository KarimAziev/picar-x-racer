from typing import List, Optional, Union

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


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
            description="The device path of the camera the mode is associated with. "
            "The path may be prefixed by an API (e.g., 'libcamera:' or 'picamera2:') to indicate "
            "the API used to interact with the device. Classic V4L2 enumeration typically "
            "results in paths such as '/dev/video0'. For APIs like libcamera or picamera2, the path may include "
            "additional information, such as 'libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a', "
            "'picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a' etc.",
            examples=[
                "/dev/video0",
                "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
                "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
            ],
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
            description="The media type. Will be used if GStreamer is installed.",
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
            "This setting should be enabled only if GStreamer is installed.",
            examples=[True, False],
        ),
    ] = False

    @model_validator(mode="after")
    def validate_dimensions(cls, values) -> Self:
        width = values.width
        height = values.height
        if (width is not None and height is None) or (
            width is None and height is not None
        ):
            raise ValueError("Both 'width' and 'height' must be specified together.")
        return values


class DeviceCommonProps(BaseModel):
    """
    Model representing common properties shared by camera devices.
    """

    device: str = Field(
        ...,
        description="The device path of the camera the mode is associated with. "
        "The path may be prefixed by an API (e.g., 'libcamera:' or 'picamera2:') to indicate "
        "the API used to interact with the device. Classic V4L2 enumeration typically "
        "results in paths such as '/dev/video0'. For APIs like libcamera or picamera2, the path may include "
        "additional information, such as 'libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a', "
        "'picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a' etc.",
        examples=[
            "/dev/video0",
            "v4l2:/dev/video0",
            "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
            "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
        ],
    )
    name: Optional[str] = Field(
        None,
        description="A human-readable name for the camera device.",
        examples=["Integrated Camera: Integrated C", "imx708_wide"],
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
            description="The media type. Will be used if GStreamer is installed.",
            examples=[
                "video/x-raw",
                "image/jpeg",
                "video/x-h264",
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


class DiscreteDevice(DeviceCommonProps):
    """
    Model representing a camera device configuration with discrete parameters.

    A "discrete" configuration specifies fixed parameters for the camera mode.
    This includes a single resolution (width, height) and a defined frame rate (fps).
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


class DeviceStepwise(DeviceCommonProps):
    """
    Model representing "stepwise" configurations, which also support "continuous" configurations.

    "Stepwise" and "continuous" configurations allow adjustable parameters like
    resolution (width, height) within a range. However, unlike "stepwise"
    configurations, "continuous" configurations allow arbitrary adjustments within
    similar ranges without the constraint of fixed step sizes.

    To represent both configurations in a unified way, "continuous" parameters are extended
    with fixed step sizes by using default minimal values - 1 px for resolutions and 1
    framerate (fps) for frame rate adjustments.
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
        1,
        title="Height Step Size",
        description="The step size in pixels for adjusting frame height.",
        examples=[1, 2, 10],
    )
    width_step: int = Field(
        1,
        title="Width Step Size",
        description="The step size in pixels for adjusting frame width.",
        examples=[1, 2, 10],
    )

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
    fps_step: Optional[float] = Field(
        1,
        title="FPS Step Size",
        description="The step size in pixels for adjusting fps.",
        examples=[1, 2, 5],
    )


DeviceType = Union[DeviceStepwise, DiscreteDevice]


class CameraDevicesResponse(BaseModel):
    """
    Successful response for available camera device configurations.
    """

    devices: List[DeviceType] = Field(
        ...,
        description=("A list of camera devices and their configurations."),
        examples=[
            [
                {
                    "device": "libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a",
                    "name": "imx708_wide",
                    "pixel_format": "NV21",
                    "media_type": "video/x-raw",
                    "api": "libcamera",
                    "path": "/base/soc/i2c0mux/i2c@1/imx708@1a",
                    "width": 640,
                    "height": 480,
                    "fps": None,
                },
                {
                    "device": "picamera2:/base/soc/i2c0mux/i2c@1/imx708@1a",
                    "name": "imx708_wide",
                    "pixel_format": "RGBx",
                    "media_type": None,
                    "api": "picamera2",
                    "path": None,
                    "min_width": 320,
                    "max_width": 4608,
                    "min_height": 240,
                    "max_height": 2592,
                    "height_step": 2,
                    "width_step": 2,
                    "min_fps": 15,
                    "max_fps": 120,
                    "fps_step": 1,
                },
                {
                    "device": "/dev/video0",
                    "name": "Integrated Camera",
                    "pixel_format": "MJPG",
                    "media_type": None,
                    "api": None,
                    "path": None,
                    "width": 1920,
                    "height": 1080,
                    "fps": 30,
                },
            ]
        ],
    )
