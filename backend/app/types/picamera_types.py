from typing import TypedDict


class GlobalCameraInfo(TypedDict):
    """
    TypedDict for camera information fields.

    Fields:
        Model: The model name of the camera, as advertised by the camera driver.
        Location: A number reporting how the camera is mounted, as reported by libcamera.
        Rotation: How the camera is rotated for normal operation, as reported by libcamera.
        Id: An identifier string for the camera, indicating how the camera is connected.
        Num: A camera index.
    """

    Model: str
    Location: int
    Rotation: int
    Id: str
    Num: int
