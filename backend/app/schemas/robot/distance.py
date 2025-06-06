from typing import Union

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
    Ultrasonic distance sensor configuration.
    """

    trig_pin: Union[str, int] = Field(
        default="D2",
        json_schema_extra={"type": "string_or_number"},
        description="The name or the number of the pin connected to the TRIG pin of the ultrasonic sensor.",
        examples=[
            "D2",
        ],
    )

    echo_pin: Union[str, int] = Field(
        default="D3",
        json_schema_extra={"type": "string_or_number"},
        description="The name or the number of the pin connected to the ECHO pin of the ultrasonic sensor.",
        examples=[
            "D3",
        ],
    )
    timeout: float = Field(
        default=0.017,
        description="The maximum duration to wait for a pulse to return.",
        gt=0,
        json_schema_extra={
            "props": {
                "step": 0.001,
                "minFractionDigits": 0,
                "maxFractionDigits": 6,
                "placeholder": "Timeout (in seconds)",
            },
        },
        examples=[
            0.1,
        ],
    )


if __name__ == "__main__":
    from pprint import pp

    print("\n\033[1m\033[32m Ultrasonic Config \033[0m\033[36mJSON schema:\033[0m")
    pp(UltrasonicConfig.model_json_schema())
