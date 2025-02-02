from app.exceptions.common import ShutdownInProgressError


class CameraRecordingError(Exception):
    pass


class CameraDeviceError(Exception):
    pass


class CameraNotFoundError(Exception):
    pass


class CameraInfoNotFound(Exception):
    pass


class CameraShutdownInProgressError(ShutdownInProgressError):
    """Raised when a camera operation is attempted but the application is shutting down."""

    pass
