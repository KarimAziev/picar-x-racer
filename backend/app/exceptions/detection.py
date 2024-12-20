class DetectionModelLoadError(Exception):
    """Exception raised when detection model is failed to load."""

    pass


class DetectionProcessError(Exception):
    """Exception raised during detection process."""

    pass


class DetectionDimensionMismatch(Exception):
    """Exception raised during dimension mismatch in detection process."""

    pass
