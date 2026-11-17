from app.exceptions.common import ShutdownInProgressError


class CameraDeviceError(Exception):
    pass


class CameraBusyError(Exception):
    """The camera is performing an operation incompatible with the request."""


class CameraFrameTimeout(TimeoutError):
    """A bounded capture read timed out without an end-of-stream or device error."""


class CameraNotFoundError(Exception):
    pass


class CameraShutdownInProgressError(ShutdownInProgressError):
    """Raised when a camera operation is attempted but the application is shutting down."""

    pass
