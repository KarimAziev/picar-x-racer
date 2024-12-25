from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


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

    Attributes:
    --------------
    - `device`: ID or name of the camera device.
    - `width`: Frame width in pixels.
    - `height`: Frame height in pixels.
    - `fps`: Frames per second for capturing.
    - `pixel_format`: Pixel format, such as 'RGB' or 'GRAY'.

    Validators:
    --------------
    - Ensures both `width` and `height` must either be specified together or not at all.
    """

    device: Optional[str] = Field(
        None,
        title="Device",
        description="The path of the camera device.",
        examples=["/dev/video0", "/dev/video1"],
    )
    width: Optional[int] = Field(
        None,
        title="Frame Width",
        description="The width of the camera frame in pixels.",
        examples=[320, 640, 800, 1024, 1280],
    )
    height: Optional[int] = Field(
        None,
        title="Frame Height",
        description="The height of the camera frame in pixels.",
        examples=[180, 480, 600, 768, 720],
    )
    fps: Optional[int] = Field(
        None,
        title="Frames Per Second",
        description="The number of frames per second the camera should capture.",
        examples=[30, 15, 20],
    )
    pixel_format: Optional[str] = Field(
        None,
        title="Pixel Format",
        description="The format for the pixels (e.g., 'RGB', 'GRAY').",
        examples=["YUYV", "MJPG", "RGB", "GRAY", "BGR"],
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


class CameraDeviceMode(BaseModel):
    """
    Model representing a specific camera mode configuration, including
    attributes such as resolution, frame rate, and pixel format.
    """

    key: str = Field(
        ...,
        description="A unique identifier for the camera mode, containing "
        "the device path, pixel format, resolution, and frame rate.",
        examples=["/dev/video0:MJPG:640x360:30", "/dev/video2:GREY:640x360:15"],
    )
    label: str = Field(
        ...,
        description="A human-readable label for the camera mode, showing the pixel format, resolution, and frame rate.",
        examples=["MJPG, 640x360, 30 fps"],
    )
    device: str = Field(
        ...,
        description="The device path of the camera the mode is associated with.",
        examples=["/dev/video0"],
    )

    size: str = Field(
        ...,
        description="The resolution of the camera mode, specified as WIDTHxHEIGHT.",
        examples=["640x360", "640x480"],
    )

    fps: int = Field(
        ...,
        description="The frame rate of the camera mode, measured in frames per second (fps).",
        examples=[10, 20, 30],
    )

    pixel_format: str = Field(
        ...,
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


class CameraDevice(BaseModel):
    """
    Model representing a camera device and its associated attributes, such as
    its unique identifier, label, and available modes.
    """

    key: str = Field(
        ...,
        description="A unique identifier for the camera device.",
        examples=["/dev/video0", "/dev/video1"],
    )
    label: str = Field(
        ...,
        description="A human-readable label for the camera device, "
        "including its device path and additional information such as the model or manufacturer.",
        examples=["/dev/video0 (Integrated Camera: Integrated C)"],
    )
    selectable: Optional[bool] = Field(
        None,
        description="Indicates whether the camera device can be selected for use. True if selectable, False otherwise.",
        examples=[False, True],
    )
    children: Optional[List[CameraDeviceMode]] = Field(
        None,
        description="A list of available camera modes (children) associated with the camera device. "
        "Each mode specifies details like resolution, frame rate, and pixel format.",
        examples=[
            [
                {
                    "key": "/dev/video0:MJPG:640x360:30",
                    "label": "MJPG, 640x360,  30 fps",
                    "device": "/dev/video0",
                    "size": "640x360",
                    "fps": 30,
                    "pixel_format": "MJPG",
                },
            ]
        ],
    )


class CameraDevicesResponse(BaseModel):
    """
    Response model for available camera devices.
    """

    devices: List[CameraDevice] = Field(
        ...,
        description=(
            "A list of devices with details such as paths, categories, and supported formats."
            "\n"
            "Each device is represented as a dictionary containing the following keys:"
            "\n"
            "`key` (device path), `label` (user-friendly name), `selectable` (whether it can be directly selected), "
            "and `children` (a list of supported formats with `key` and `label`)."
        ),
        examples=[
            [
                {
                    "key": "/dev/video0",
                    "label": "/dev/video0 (Integrated Camera: Integrated C)",
                    "selectable": False,
                    "children": [
                        {
                            "key": "/dev/video0:MJPG:640x360:30",
                            "label": "MJPG, 640x360,  30 fps",
                            "device": "/dev/video0",
                            "size": "640x360",
                            "fps": 30,
                            "pixel_format": "MJPG",
                        },
                        {
                            "key": "/dev/video0:YUYV:640x360:30",
                            "label": "YUYV, 640x360,  30 fps",
                            "device": "/dev/video0",
                            "size": "640x360",
                            "fps": 30,
                            "pixel_format": "YUYV",
                        },
                    ],
                },
                {
                    "key": "/dev/video2",
                    "label": "/dev/video2 (Integrated Camera: Integrated C)",
                    "selectable": False,
                    "children": [
                        {
                            "key": "/dev/video2:GREY:640x360:15",
                            "label": "GREY, 640x360,  15 fps",
                            "device": "/dev/video2",
                            "size": "640x360",
                            "fps": 15,
                            "pixel_format": "GREY",
                        },
                    ],
                },
            ]
        ],
    )
