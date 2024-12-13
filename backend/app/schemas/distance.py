from pydantic import BaseModel, Field


class DistanceData(BaseModel):
    """
    A model to represent the distance data measured by the ultrasonic sensor.

    Attributes:
    - `distance`: The measured distance is in centimeters.
    Possible Values:
    Positive float values: Represent the measured distance in centimeters (e.g., 120.5).
     -1: Indicates no object was detected (timeout).
     -2: Measurement failed due to invalid conditions.
    """

    distance: float = Field(
        ...,
        description="The measured distance in centimeters",
        examples=[
            120.5,  # Successful measurement
            -1,  # No object detected (timeout)
            -2,  # Object too close (< 2 cm) or invalid conditions
        ],
    )
