class ShutdownInProgressError(Exception):
    """Raised when an operation is attempted but the application is shutting down."""

    pass
