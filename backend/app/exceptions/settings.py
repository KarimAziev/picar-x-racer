class InvalidSettings(ValueError):
    """
    Exception raised when attempting to save invalid settings.
    """

    pass


class UnchangedSettings(InvalidSettings):
    """
    Exception raised when attempting to save settings that are identical to the current settings.
    """

    pass
