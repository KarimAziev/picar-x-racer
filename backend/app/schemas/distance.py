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


class UltrasonicConfig(BaseModel):
    """
    A model to represent the Ultrasonic configuration.
    """

    trig_pin: str = Field(
        default="D2",
        description="The name of the pin connected to the TRIG pin of the ultrasonic sensor.",
        examples=[
            "D2",
        ],
    )

    echo_pin: str = Field(
        default="D3",
        description="The name of the pin connected to the ECHO pin of the ultrasonic sensor.",
        examples=[
            "D3",
        ],
    )
    timeout: float = Field(
        default=0.017,
        description="The maximum duration to wait for a pulse to return.",
        examples=[
            0.1,
        ],
    )
