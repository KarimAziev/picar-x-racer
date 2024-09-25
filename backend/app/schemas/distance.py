from pydantic import BaseModel


class DistanceData(BaseModel):
    distance: float
