"""Libcamera exposure and focus controls for Picamera2."""

from typing import Mapping, Sequence

from app.schemas.camera_controls import (
    CameraControls,
    CameraControlCapabilities,
    ControlRange,
)


def picamera_control_capabilities(
    info: Mapping[str, Sequence[float]]
) -> CameraControlCapabilities:
    caps = CameraControlCapabilities()
    if "AeEnable" in info:
        caps.exposure_modes.append("auto")
        if "ExposureTime" in info:
            low, high = info["ExposureTime"][:2]
            caps.exposure_modes.append("manual")
            caps.exposure_time_us = ControlRange(min=low, max=high, step=1, unit="µs")
    if "AfMode" in info:
        low, high = info["AfMode"][:2]
        if low <= 2 <= high:
            caps.focus_modes.append("auto")
        if low <= 0 <= high and "LensPosition" in info:
            low, high = info["LensPosition"][:2]
            caps.focus_modes.append("manual")
            caps.focus_position = ControlRange(min=low, max=high, unit="dioptres")
    return caps


def picamera_control_values(controls: CameraControls) -> dict[str, float | int | bool]:
    values: dict[str, float | int | bool] = {}
    if controls.exposure_mode is not None:
        values["AeEnable"] = controls.exposure_mode == "auto"
        if controls.exposure_time_us is not None:
            values["ExposureTime"] = controls.exposure_time_us
    if controls.focus_mode is not None:
        values["AfMode"] = 2 if controls.focus_mode == "auto" else 0
        if controls.focus_position is not None:
            values["LensPosition"] = controls.focus_position
    return values
