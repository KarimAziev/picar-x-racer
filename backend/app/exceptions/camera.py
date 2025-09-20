from app.exceptions.common import ShutdownInProgressError


class CameraDeviceError(Exception):
    pass


class CameraNotFoundError(Exception):
    pass


class CameraShutdownInProgressError(ShutdownInProgressError):
    """Raised when a camera operation is attempted but the application is shutting down."""

    pass
