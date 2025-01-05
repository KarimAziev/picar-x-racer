from __future__ import annotations

from typing import List, Optional, Union

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


class DeviceItem(BaseModel):
    """
    A model representing a camera device item, which serves as a base for other device-related models.
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


class DeviceCommonProps(BaseModel):
    """
    Model representing common properties shared by camera devices.
    """

    device: str = Field(
        ...,
        description="The device path of the camera the mode is associated with.",
        examples=["/dev/video0"],
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
    fps: int = Field(
        ...,
        description="The frame rate of the camera mode, measured in frames per second (fps).",
        examples=[10, 20, 30],
    )


class DeviceStepwise(DeviceItem, DeviceCommonProps):
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

    min_fps: int = Field(
        ...,
        description="The minimal frame rate of the camera mode, measured in frames per second (fps).",
        examples=[1, 20, 30],
    )

    max_fps: int = Field(
        ...,
        description="The maximum frame rate of the camera mode, measured in frames per second (fps).",
        examples=[90],
    )


class DeviceNode(DeviceItem):
    """
    A model representing a node in the device hierarchy, which may contain child
    nodes or configurations such as stepwise or discrete properties.
    """

    children: List[Union[DeviceStepwise, DeviceNode, DiscreteDevice]] = Field(
        ...,
        description=(
            "A list of child nodes or configurations, "
            "which can include stepwise configurations, discrete configurations, or other nested nodes."
        ),
        examples=[
            [
                {
                    'key': '/dev/video0:MJPG',
                    'label': 'MJPG',
                    'children': [
                        {
                            'key': '/dev/video0:MJPG:352x288:30',
                            'label': 'MJPG, 352x288,  30 fps',
                            'device': '/dev/video0',
                            'width': 352,
                            'height': 288,
                            'fps': 30,
                            'pixel_format': 'MJPG',
                        },
                    ],
                },
                {
                    'key': '/dev/video1',
                    'label': '/dev/video1 (mmal service 16.1)',
                    'children': [
                        {
                            'key': '/dev/video1:YU12:32x32 - 2592x1944',
                            'label': 'YU12 32x32 - 2592x1944',
                            'device': '/dev/video1',
                            'pixel_format': 'YU12',
                            'min_width': 32,
                            'max_width': 2592,
                            'min_height': 32,
                            'max_height': 1944,
                            'height_step': 2,
                            'width_step': 2,
                            'min_fps': 1,
                            'max_fps': 90,
                        },
                        {
                            'key': '/dev/video1:YUYV:32x32 - 2592x1944',
                            'label': 'YUYV 32x32 - 2592x1944',
                            'device': '/dev/video1',
                            'pixel_format': 'YUYV',
                            'min_width': 32,
                            'max_width': 2592,
                            'min_height': 32,
                            'max_height': 1944,
                            'height_step': 2,
                            'width_step': 2,
                            'min_fps': 1,
                            'max_fps': 90,
                        },
                    ],
                },
            ]
        ],
    )


class CameraDevicesResponse(BaseModel):
    """
    Response model for available camera devices.
    """

    devices: List[DeviceNode] = Field(
        ...,
        description=(
            "A hierarchical list of camera devices and their configurations, "
            "where each device can have child nodes or configurable properties."
        ),
        examples=[
            {
                "devices": [
                    {
                        'key': '/dev/video0',
                        'label': '/dev/video0 (Integrated Camera: Integrated C)',
                        'children': [
                            {
                                'key': '/dev/video0:MJPG',
                                'label': 'MJPG',
                                'children': [
                                    {
                                        'key': '/dev/video0:MJPG:352x288:30',
                                        'label': 'MJPG, 352x288,  30 fps',
                                        'device': '/dev/video0',
                                        'width': 352,
                                        'height': 288,
                                        'fps': 30,
                                        'pixel_format': 'MJPG',
                                    },
                                    {
                                        'key': '/dev/video0:MJPG:424x240:30',
                                        'label': 'MJPG, 424x240,  30 fps',
                                        'device': '/dev/video0',
                                        'width': 424,
                                        'height': 240,
                                        'fps': 30,
                                        'pixel_format': 'MJPG',
                                    },
                                ],
                            },
                            {
                                'key': '/dev/video0:YUYV',
                                'label': 'YUYV',
                                'children': [
                                    {
                                        'key': '/dev/video0:YUYV:640x480:30',
                                        'label': 'YUYV, 640x480,  30 fps',
                                        'device': '/dev/video0',
                                        'width': 640,
                                        'height': 480,
                                        'fps': 30,
                                        'pixel_format': 'YUYV',
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        'key': '/dev/video2',
                        'label': '/dev/video2 (Integrated Camera: Integrated C)',
                        'children': [
                            {
                                'key': '/dev/video2:GREY:640x360:15',
                                'label': 'GREY, 640x360,  15 fps',
                                'device': '/dev/video2',
                                'width': 640,
                                'height': 360,
                                'fps': 15,
                                'pixel_format': 'GREY',
                            }
                        ],
                    },
                    {
                        'key': '/dev/video1',
                        'label': '/dev/video1 (mmal service 16.1)',
                        'children': [
                            {
                                'key': '/dev/video1:YU12:32x32 - 2592x1944',
                                'label': 'YU12 32x32 - 2592x1944',
                                'device': '/dev/video1',
                                'pixel_format': 'YU12',
                                'min_width': 32,
                                'max_width': 2592,
                                'min_height': 32,
                                'max_height': 1944,
                                'height_step': 2,
                                'width_step': 2,
                                'min_fps': 1,
                                'max_fps': 90,
                            },
                            {
                                'key': '/dev/video1:YUYV:32x32 - 2592x1944',
                                'label': 'YUYV 32x32 - 2592x1944',
                                'device': '/dev/video1',
                                'pixel_format': 'YUYV',
                                'min_width': 32,
                                'max_width': 2592,
                                'min_height': 32,
                                'max_height': 1944,
                                'height_step': 2,
                                'width_step': 2,
                                'min_fps': 1,
                                'max_fps': 90,
                            },
                        ],
                    },
                ]
            }
        ],
    )
