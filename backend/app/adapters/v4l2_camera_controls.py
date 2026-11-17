"""V4L2 controls shared by native and GStreamer capture."""

import fcntl
import os
from typing import Optional

import v4l2

from app.exceptions.camera import CameraDeviceError
from app.schemas.camera_controls import (
    CameraControls,
    CameraControlCapabilities,
    ControlRange,
)

EXPOSURE_MODE = v4l2.V4L2_CID_EXPOSURE_AUTO
EXPOSURE_TIME = v4l2.V4L2_CID_EXPOSURE_ABSOLUTE
FOCUS_MODE = v4l2.V4L2_CID_FOCUS_AUTO
FOCUS_POSITION = v4l2.V4L2_CID_FOCUS_ABSOLUTE


class V4L2CameraControls:
    def __init__(self, device: str):
        try:
            self.fd: Optional[int] = os.open(device, os.O_RDWR | os.O_NONBLOCK)
        except OSError as error:
            raise CameraDeviceError(
                f"Cannot inspect camera controls: {error}"
            ) from error
        self.saved: dict[int, int] = {}
        self.info = {}
        for control_id in (EXPOSURE_MODE, EXPOSURE_TIME, FOCUS_MODE, FOCUS_POSITION):
            query = v4l2.v4l2_queryctrl()
            query.id = control_id
            try:
                fcntl.ioctl(self.fd, v4l2.VIDIOC_QUERYCTRL, query)
                if not query.flags & (
                    v4l2.V4L2_CTRL_FLAG_DISABLED | v4l2.V4L2_CTRL_FLAG_READ_ONLY
                ):
                    self.info[control_id] = query
            except OSError:
                pass
        self.exposure_auto = self._menu_value([3, 0])
        self.exposure_manual = self._menu_value([1, 2])

    def _menu_value(self, candidates: list[int]) -> Optional[int]:
        if EXPOSURE_MODE not in self.info or self.fd is None:
            return None
        for value in candidates:
            query = v4l2.v4l2_querymenu()
            query.id, query.index = EXPOSURE_MODE, value
            try:
                fcntl.ioctl(self.fd, v4l2.VIDIOC_QUERYMENU, query)
                return value
            except OSError:
                pass
        return None

    def _range(self, control_id: int, scale: int, unit: str) -> Optional[ControlRange]:
        info = self.info.get(control_id)
        if info is None:
            return None
        return ControlRange(
            min=info.minimum * scale,
            max=info.maximum * scale,
            step=info.step * scale,
            unit=unit,
        )

    @property
    def capabilities(self) -> CameraControlCapabilities:
        caps = CameraControlCapabilities(
            exposure_time_us=self._range(EXPOSURE_TIME, 100, "µs"),
            focus_position=self._range(FOCUS_POSITION, 1, "device units"),
        )
        if self.exposure_auto is not None:
            caps.exposure_modes.append("auto")
        if self.exposure_manual is not None and caps.exposure_time_us:
            caps.exposure_modes.append("manual")
        if FOCUS_MODE in self.info:
            caps.focus_modes.append("auto")
        if caps.focus_position:
            caps.focus_modes.append("manual")
        return caps

    def _get(self, control_id: int) -> int:
        control = v4l2.v4l2_control()
        control.id = control_id
        if self.fd is None:
            raise CameraDeviceError("Camera controls are closed")
        fcntl.ioctl(self.fd, v4l2.VIDIOC_G_CTRL, control)
        return int(control.value)

    def _set(self, control_id: int, value: int) -> None:
        control = v4l2.v4l2_control()
        control.id, control.value = control_id, value
        if self.fd is None:
            raise CameraDeviceError("Camera controls are closed")
        fcntl.ioctl(self.fd, v4l2.VIDIOC_S_CTRL, control)
        actual = self._get(control_id)
        if actual != value:
            raise CameraDeviceError(
                f"Camera rejected control {control_id}: requested {value}, received {actual}"
            )

    def apply(self, controls: CameraControls) -> None:
        self.capabilities.validate_controls(controls)
        ids = (
            [] if controls.exposure_mode is None else [EXPOSURE_MODE, EXPOSURE_TIME]
        ) + ([] if controls.focus_mode is None else [FOCUS_MODE, FOCUS_POSITION])
        try:
            self.saved = {key: self._get(key) for key in ids if key in self.info}
            if controls.exposure_mode is not None:
                mode = (
                    self.exposure_auto
                    if controls.exposure_mode == "auto"
                    else self.exposure_manual
                )
                if mode is not None:
                    self._set(EXPOSURE_MODE, mode)
                if controls.exposure_time_us is not None:
                    self._set(EXPOSURE_TIME, controls.exposure_time_us // 100)
            if controls.focus_mode is not None:
                if FOCUS_MODE in self.info:
                    self._set(FOCUS_MODE, int(controls.focus_mode == "auto"))
                if controls.focus_position is not None:
                    self._set(FOCUS_POSITION, int(controls.focus_position))
        except OSError as error:
            raise CameraDeviceError(f"Cannot apply camera controls: {error}") from error

    def close(self) -> None:
        if self.fd is None:
            return
        try:
            for mode_id, value_id, manual_modes in (
                (EXPOSURE_MODE, EXPOSURE_TIME, (1, 2)),
                (FOCUS_MODE, FOCUS_POSITION, (0,)),
            ):
                if mode_id in self.saved:
                    self._set(mode_id, self.saved[mode_id])
                if value_id in self.saved and (
                    mode_id not in self.saved or self.saved[mode_id] in manual_modes
                ):
                    self._set(value_id, self.saved[value_id])
        finally:
            os.close(self.fd)
            self.fd = None
            self.saved = {}
