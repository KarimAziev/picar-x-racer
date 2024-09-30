from pydantic import BaseModel


class DistanceData(BaseModel):
    """
    A model to represent the distance data measured by the ultrasonic sensor.

    Attributes:
    - `distance` (float): The measured distance in centimeters.
    """

    distance: float
