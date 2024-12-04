from pydantic import BaseModel, Field, field_validator


class VolumeData(BaseModel):
    """
    Schema for volume level requests and responses.

    Attributes:
    --------------
    - `volume` (int): The desired or current volume level, represented as an integer between 0 and 100.

    Behavior:
    --------------
    - If the input is a float (e.g., `45.6`), it is converted to an integer (rounded to the nearest whole number, e.g., `46`).
    - Only integers between 0 and 100 are accepted; fractional inputs like `0.99` will normalize to `1`.
    - If the volume has more than one decimal place or is not a number, an error is raised.

    Example Inputs:
    --------------
    - Valid Inputs: `{"volume": 45}`, `{"volume": 45.6}`, `{"volume": 0.9}`
    - Invalid Inputs: `{"volume": -1}`, `{"volume": 101}`, `{"volume": 50.123}`
    """

    volume: int = Field(
        ..., ge=0, le=100, description="Volume must be between 0 and 100 as an integer"
    )

    @field_validator("volume", mode="before")
    def process_volume(cls, value):
        """
        Validates and processes the `volume` field.

        Converts float input to an integer to normalize volume handling,
        with a range of 0-100.

        Args:
        --------------
        - `value` (Union[int, float]): The volume level to validate.

        Returns:
        --------------
        - `value` (int): The normalized volume level as an integer.

        Raises:
        --------------
        - `ValueError`: If the decimal precision is invalid (more than 1 decimal place)
                        or if the value is out of the accepted range (0-100).
        """
        if isinstance(value, float):
            if len(str(value).split(".")[1]) > 1:
                raise ValueError("Volume decimal precision must be at most 1.")
            return round(value)
        elif isinstance(value, int):
            return value
        raise ValueError("Volume must be a number.")
