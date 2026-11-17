"""Portable camera control requests and device-reported limits."""

import math
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from app.exceptions.camera import CameraDeviceError

ControlMode = Literal["auto", "manual"]


class CameraControls(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exposure_mode: Optional[ControlMode] = None
    exposure_time_us: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    focus_mode: Optional[ControlMode] = None
    focus_position: Optional[float] = Field(default=None, allow_inf_nan=False)

    @property
    def requested(self) -> bool:
        return self.exposure_mode is not None or self.focus_mode is not None

    @model_validator(mode="after")
    def validate_modes(self) -> Self:
        for name, mode, value in (
            ("exposure_time_us", self.exposure_mode, self.exposure_time_us),
            ("focus_position", self.focus_mode, self.focus_position),
        ):
            if (mode == "manual") != (value is not None):
                raise ValueError(
                    f"{name} must be provided exactly when its mode is manual"
                )
        return self


class ControlRange(BaseModel):
    min: float
    max: float
    step: Optional[float] = None
    unit: str

    def validate_value(self, name: str, value: float) -> None:
        if not self.min <= value <= self.max:
            raise CameraDeviceError(
                f"{name} must be between {self.min:g} and {self.max:g} {self.unit}."
            )
        if self.step and not math.isclose(
            (value - self.min) / self.step,
            round((value - self.min) / self.step),
            abs_tol=1e-6,
        ):
            raise CameraDeviceError(
                f"{name} must use steps of {self.step:g} {self.unit} from {self.min:g}."
            )


class CameraControlCapabilities(BaseModel):
    exposure_modes: list[ControlMode] = Field(default_factory=list)
    exposure_time_us: Optional[ControlRange] = None
    focus_modes: list[ControlMode] = Field(default_factory=list)
    focus_position: Optional[ControlRange] = None
    message: Optional[str] = None

    def validate_controls(self, controls: CameraControls) -> None:
        for name, mode, modes, value, limits in (
            (
                "Exposure",
                controls.exposure_mode,
                self.exposure_modes,
                controls.exposure_time_us,
                self.exposure_time_us,
            ),
            (
                "Focus",
                controls.focus_mode,
                self.focus_modes,
                controls.focus_position,
                self.focus_position,
            ),
        ):
            if mode is not None and mode not in modes:
                raise CameraDeviceError(
                    f"{name} mode '{mode}' is not supported by this camera backend."
                )
            if value is not None:
                if limits is None:
                    raise CameraDeviceError(
                        f"Manual {name.lower()} is not supported by this camera."
                    )
                limits.validate_value(name, value)
