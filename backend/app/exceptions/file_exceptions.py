class DefaultFileRemoveAttempt(Exception):
    """Exception raised when default file is trying to remove."""

    pass


class InvalidFileName(Exception):
    """
    Exception raised when uploaded file has an invalid name.
    """

    pass


class InvalidMediaType(Exception):
    """
    Exception raised on unsupported media type upload attempt.
    """

    pass
