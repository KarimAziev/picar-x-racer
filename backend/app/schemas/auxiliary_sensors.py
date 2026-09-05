"""API representations for auxiliary sensor telemetry."""

from typing import Literal, Optional, Tuple

from pydantic import BaseModel, Field
from typing_extensions import Annotated


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
Vector3 = Tuple[FiniteFloat, FiniteFloat, FiniteFloat]


class AuxiliarySensorReading(BaseModel):
    name: str
    driver: str
    kind: Literal["environmental", "magnetometer"]
    timestamp_monotonic_ns: Optional[int] = None
    temperature_c: Optional[FiniteFloat] = None
    relative_humidity_percent: Annotated[
        Optional[float], Field(ge=0, le=100, allow_inf_nan=False)
    ] = None
    pressure_pa: Annotated[Optional[float], Field(ge=0, allow_inf_nan=False)] = None
    magnetic_field_t: Optional[Vector3] = None
    error: Optional[str] = None


__all__ = ["AuxiliarySensorReading"]
