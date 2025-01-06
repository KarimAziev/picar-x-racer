class DetectionModelLoadError(Exception):
    """Exception raised when a detection model fails to load."""

    pass


class DetectionProcessError(Exception):
    """Exception raised during the detection process."""

    pass


class DetectionDimensionMismatch(Exception):
    """Exception raised due to a dimension mismatch in the detection process."""

    pass


class DetectionProcessLoading(Exception):
    """Exception raised when attempting to update a process that is still loading."""

    pass


class DetectionProcessClosing(Exception):
    """Exception raised when attempting to update a detection process that is about to close."""

    pass
