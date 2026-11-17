"""Native AVFoundation camera control capabilities and restoration."""

from typing import Any

from app.exceptions.camera import CameraDeviceError
from app.schemas.camera_controls import (
    CameraControls,
    CameraControlCapabilities,
    ControlRange,
)


class AVFoundationCameraControls:
    def __init__(self, device: Any, frameworks: tuple[Any, Any]):
        self.device = device
        self.av, self.cm = frameworks
        self.saved: dict[str, Any] = {}

    @property
    def capabilities(self) -> CameraControlCapabilities:
        caps = CameraControlCapabilities()
        av, device = self.av, self.device
        if device.isExposureModeSupported_(
            av.AVCaptureExposureModeContinuousAutoExposure
        ):
            caps.exposure_modes.append("auto")
        if device.isExposureModeSupported_(av.AVCaptureExposureModeCustom):
            fmt = device.activeFormat()
            caps.exposure_time_us = ControlRange(
                min=self.cm.CMTimeGetSeconds(fmt.minExposureDuration()) * 1_000_000,
                max=self.cm.CMTimeGetSeconds(fmt.maxExposureDuration()) * 1_000_000,
                unit="µs",
            )
            caps.exposure_modes.append("manual")
        if device.isFocusModeSupported_(av.AVCaptureFocusModeContinuousAutoFocus):
            caps.focus_modes.append("auto")
        if (
            device.isFocusModeSupported_(av.AVCaptureFocusModeLocked)
            and device.isLockingFocusWithCustomLensPositionSupported()
        ):
            caps.focus_modes.append("manual")
            caps.focus_position = ControlRange(min=0, max=1, unit="lens position")
        if not caps.exposure_modes and not caps.focus_modes:
            caps.message = "This camera does not expose exposure or focus controls through AVFoundation."
        return caps

    def _lock(self) -> None:
        success, error = self.device.lockForConfiguration_(None)
        if not success:
            raise CameraDeviceError(f"Cannot lock camera controls: {error}")

    def apply(self, controls: CameraControls) -> None:
        self.capabilities.validate_controls(controls)
        self._lock()
        device, av = self.device, self.av
        try:
            if controls.exposure_mode is not None:
                self.saved["exposure_mode"] = device.exposureMode()
                if self.saved["exposure_mode"] == av.AVCaptureExposureModeCustom:
                    self.saved["duration"] = device.exposureDuration()
                    self.saved["iso"] = device.ISO()
            if controls.focus_mode is not None:
                self.saved["focus_mode"] = device.focusMode()
                if self.saved["focus_mode"] == av.AVCaptureFocusModeLocked:
                    self.saved["position"] = device.lensPosition()
            if controls.exposure_mode == "auto":
                device.setExposureMode_(av.AVCaptureExposureModeContinuousAutoExposure)
            elif controls.exposure_time_us is not None:
                device.setExposureModeCustomWithDuration_ISO_completionHandler_(
                    self.cm.CMTimeMake(controls.exposure_time_us, 1_000_000),
                    av.AVCaptureISOCurrent,
                    None,
                )
            if controls.focus_mode == "auto":
                device.setFocusMode_(av.AVCaptureFocusModeContinuousAutoFocus)
            elif controls.focus_position is not None:
                device.setFocusModeLockedWithLensPosition_completionHandler_(
                    controls.focus_position, None
                )
        except Exception as error:
            raise CameraDeviceError(f"Cannot apply camera controls: {error}") from error
        finally:
            device.unlockForConfiguration()

    def close(self) -> None:
        if not self.saved:
            return
        self._lock()
        try:
            if "duration" in self.saved:
                self.device.setExposureModeCustomWithDuration_ISO_completionHandler_(
                    self.saved["duration"], self.saved["iso"], None
                )
            elif "exposure_mode" in self.saved:
                self.device.setExposureMode_(self.saved["exposure_mode"])
            if "position" in self.saved:
                self.device.setFocusModeLockedWithLensPosition_completionHandler_(
                    self.saved["position"], None
                )
            elif "focus_mode" in self.saved:
                self.device.setFocusMode_(self.saved["focus_mode"])
        finally:
            self.saved = {}
            self.device.unlockForConfiguration()
