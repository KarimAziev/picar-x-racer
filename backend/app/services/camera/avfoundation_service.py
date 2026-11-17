from functools import lru_cache
from typing import Any, List, Optional, Sequence, Tuple
from pydantic import ValidationError

from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.video_device_abc import VideoDeviceABC
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.schemas.camera import (
    CameraSettings,
    DeviceStepwise,
    DeviceType,
    DiscreteDevice,
)
from app.util.os_checks import is_macos
from app.adapters.avfoundation_camera_controls import AVFoundationCameraControls

_log = Logger(name=__name__)

_DISCOVERY_DEVICE_TYPE_NAMES = (
    "AVCaptureDeviceTypeBuiltInWideAngleCamera",
    "AVCaptureDeviceTypeContinuityCamera",
    "AVCaptureDeviceTypeDeskViewCamera",
    "AVCaptureDeviceTypeExternal",
    "AVCaptureDeviceTypeExternalUnknown",
)


class AVFoundationService(VideoDeviceABC):
    def camera_controls(self, device: str) -> AVFoundationCameraControls:
        frameworks = self._load_frameworks()
        unique_id = GStreamerParser.strip_api_prefix(device).lstrip("/")
        if frameworks is not None:
            for item in self._discover_devices():
                if str(item.uniqueID()) == unique_id:
                    return AVFoundationCameraControls(item, frameworks)
        raise CameraNotFoundError("AVFoundation camera device is not available")

    @staticmethod
    def _round_fps(value: float) -> float:
        return round(float(value), 3)

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_frameworks() -> Optional[Tuple[Any, Any]]:
        if not is_macos():
            return None
        try:
            import AVFoundation  # type: ignore
            import CoreMedia  # type: ignore
        except ImportError:
            _log.warning("PyObjC AVFoundation bindings are not installed")
            return None
        except Exception:
            _log.warning(
                "Unexpected error while importing AVFoundation bindings",
                exc_info=True,
            )
            return None
        return AVFoundation, CoreMedia

    @classmethod
    def available(cls) -> bool:
        return cls._load_frameworks() is not None

    @staticmethod
    def fourcc_to_str(fourcc: int) -> str:
        text = "".join(chr((fourcc >> shift) & 0xFF) for shift in (24, 16, 8, 0))
        return text if all(31 < ord(ch) < 127 for ch in text) else hex(fourcc)

    def _discover_devices(self) -> List[Any]:
        frameworks = self._load_frameworks()
        if frameworks is None:
            return []

        AVFoundation, _ = frameworks
        device_types = [
            getattr(AVFoundation, name)
            for name in _DISCOVERY_DEVICE_TYPE_NAMES
            if hasattr(AVFoundation, name)
        ]

        try:
            if device_types:
                discovery_session = AVFoundation.AVCaptureDeviceDiscoverySession.discoverySessionWithDeviceTypes_mediaType_position_(
                    device_types,
                    AVFoundation.AVMediaTypeVideo,
                    AVFoundation.AVCaptureDevicePositionUnspecified,
                )
                return list(discovery_session.devices() or [])
            return list(
                AVFoundation.AVCaptureDevice.devicesWithMediaType_(
                    AVFoundation.AVMediaTypeVideo
                )
                or []
            )
        except Exception:
            _log.error("Failed to discover AVFoundation devices", exc_info=True)
            return []

    def resolve_capture_index(self, device: str) -> int:
        unique_id = GStreamerParser.strip_api_prefix(device).lstrip("/")
        for index, item in enumerate(self._discover_devices()):
            if str(item.uniqueID()) == unique_id:
                return index
        raise CameraNotFoundError("AVFoundation camera device is not available")

    @classmethod
    def _extract_candidate_fps(cls, frame_ranges: Sequence[Any]) -> List[float]:
        if not frame_ranges:
            return []

        # FFmpeg's avfoundation input accepts the exact max frame rate for these
        # camera modes reliably on macOS, while lower in-range values like 15 FPS
        # can still be rejected even when AVFoundation reports a 15-30 range.
        max_fps = max(
            cls._round_fps(float(item.maxFrameRate())) for item in frame_ranges
        )
        return [max_fps]

    def _build_profiles(self, device: Any, core_media: Any) -> List[DeviceType]:
        localized_name = str(device.localizedName())
        unique_id = str(device.uniqueID())
        device_path = f"/{unique_id}"
        full_device = f"avfoundation:{device_path}"
        results: List[DeviceType] = []
        seen: set[Tuple[Any, ...]] = set()

        for fmt in list(device.formats() or []):
            try:
                format_description = fmt.formatDescription()
                dimensions = core_media.CMVideoFormatDescriptionGetDimensions(
                    format_description
                )
                width = int(dimensions.width)
                height = int(dimensions.height)
                if width <= 0 or height <= 0:
                    continue

                subtype = core_media.CMFormatDescriptionGetMediaSubType(
                    format_description
                )
                pixel_format = self.fourcc_to_str(int(subtype))
                common = {
                    "device": full_device,
                    "name": localized_name,
                    "pixel_format": pixel_format,
                    "media_type": "video/x-raw",
                    "api": "avfoundation",
                    "path": device_path,
                }

                frame_ranges = list(fmt.videoSupportedFrameRateRanges() or [])
                if not frame_ranges:
                    dedupe_key = (
                        full_device,
                        pixel_format,
                        width,
                        height,
                        None,
                        None,
                        "discrete",
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    results.append(
                        DiscreteDevice(
                            **common,
                            width=width,
                            height=height,
                            fps=None,
                        )
                    )
                    continue

                candidate_fps = self._extract_candidate_fps(frame_ranges)
                if not candidate_fps:
                    continue

                if len(candidate_fps) == 1:
                    fps = candidate_fps[0]
                    dedupe_key = (
                        full_device,
                        pixel_format,
                        width,
                        height,
                        fps,
                        None,
                        "discrete",
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    results.append(
                        DiscreteDevice(
                            **common,
                            width=width,
                            height=height,
                            fps=fps,
                        )
                    )
                else:
                    for fps in candidate_fps:
                        dedupe_key = (
                            full_device,
                            pixel_format,
                            width,
                            height,
                            fps,
                            None,
                            "discrete",
                        )
                        if dedupe_key in seen:
                            continue
                        seen.add(dedupe_key)
                        results.append(
                            DiscreteDevice(
                                **common,
                                width=width,
                                height=height,
                                fps=fps,
                            )
                        )
            except Exception:
                _log.error(
                    "Failed to inspect AVFoundation camera format for '%s'",
                    localized_name,
                    exc_info=True,
                )

        return results

    def list_video_devices(self) -> List[DeviceType]:
        frameworks = self._load_frameworks()
        if frameworks is None:
            return []

        _, core_media = frameworks
        devices = self._discover_devices()
        detected: List[DeviceType] = []
        for device in devices:
            detected.extend(self._build_profiles(device, core_media))

        def sort_key(item: DeviceType) -> Tuple[str, int, int, float]:
            width = item.width if isinstance(item, DiscreteDevice) else item.min_width
            height = (
                item.height if isinstance(item, DiscreteDevice) else item.min_height
            )
            fps = item.fps if isinstance(item, DiscreteDevice) else item.max_fps
            return (item.name or item.device, width, height, float(fps or 0.0))

        return sorted(detected, key=sort_key)

    @staticmethod
    def _score_profile(
        profile: DeviceType, camera_settings: CameraSettings
    ) -> Tuple[int, int, float, float]:
        exact_pixel_format = (
            1
            if camera_settings.pixel_format is not None
            and camera_settings.pixel_format == profile.pixel_format
            else 0
        )
        exact_fps = 0
        fps_distance = 0.0
        if camera_settings.fps is not None:
            if isinstance(profile, DiscreteDevice):
                profile_fps = float(profile.fps or 0.0)
                fps_distance = -abs(profile_fps - float(camera_settings.fps))
                exact_fps = int(abs(profile_fps - float(camera_settings.fps)) < 0.001)
            else:
                exact_fps = int(
                    profile.min_fps <= camera_settings.fps <= profile.max_fps
                )
                if exact_fps == 0:
                    fps_distance = -min(
                        abs(float(profile.min_fps) - float(camera_settings.fps)),
                        abs(float(profile.max_fps) - float(camera_settings.fps)),
                    )

        fallback_fps = (
            float(profile.fps or 0.0)
            if isinstance(profile, DiscreteDevice)
            else float(profile.max_fps)
        )
        return (exact_pixel_format, exact_fps, fps_distance, fallback_fps)

    @staticmethod
    def _matches_profile(profile: DeviceType, camera_settings: CameraSettings) -> bool:
        if (
            camera_settings.pixel_format is not None
            and profile.pixel_format is not None
            and profile.pixel_format != camera_settings.pixel_format
        ):
            return False

        if camera_settings.width is not None and camera_settings.height is not None:
            if isinstance(profile, DiscreteDevice):
                if (
                    profile.width != camera_settings.width
                    or profile.height != camera_settings.height
                ):
                    return False
            else:
                if not (
                    profile.min_width <= camera_settings.width <= profile.max_width
                    and profile.min_height
                    <= camera_settings.height
                    <= profile.max_height
                ):
                    return False

        if camera_settings.fps is None:
            return True

        if isinstance(profile, DiscreteDevice):
            return True

        return profile.min_fps <= camera_settings.fps <= profile.max_fps

    def _select_profile(
        self, device_profiles: Sequence[DeviceType], camera_settings: CameraSettings
    ) -> Optional[DeviceType]:
        matching_profiles = [
            item
            for item in device_profiles
            if self._matches_profile(item, camera_settings)
        ]
        if matching_profiles:
            return max(
                matching_profiles,
                key=lambda item: self._score_profile(item, camera_settings),
            )
        if (
            device_profiles
            and camera_settings.width is None
            and camera_settings.height is None
        ):
            return device_profiles[0]
        return None

    @staticmethod
    def _format_modes(device_profiles: Sequence[DeviceType]) -> str:
        modes: List[str] = []
        for item in device_profiles:
            if isinstance(item, DiscreteDevice):
                fps = f"@{item.fps:g}FPS" if item.fps is not None else ""
                modes.append(f"{item.width}x{item.height}{fps}")
            else:
                fps = f"@{item.min_fps:g}-{item.max_fps:g}FPS"
                modes.append(f"{item.min_width}x{item.min_height}{fps}")
        return ", ".join(modes)

    def resolve_capture_config(
        self, device: str, camera_settings: CameraSettings
    ) -> Tuple[str, CameraSettings]:
        unique_id = GStreamerParser.strip_api_prefix(device).lstrip("/")
        av_device = next(
            (
                item
                for item in self._discover_devices()
                if str(item.uniqueID()) == unique_id
            ),
            None,
        )
        if av_device is None:
            raise CameraNotFoundError("AVFoundation camera device is not available")

        full_device = f"avfoundation:/{unique_id}"
        device_profiles = [
            item for item in self.list_video_devices() if item.device == full_device
        ]
        selected_profile = self._select_profile(device_profiles, camera_settings)
        if selected_profile is None and device_profiles:
            supported_modes = self._format_modes(device_profiles)
            raise CameraDeviceError(
                "Requested camera mode is not supported on macOS. "
                f"Available modes: {supported_modes}"
            )

        updated_settings = camera_settings.model_dump()
        updated_settings["device"] = full_device
        updated_settings["use_gstreamer"] = False

        if isinstance(selected_profile, DiscreteDevice):
            updated_settings["width"] = selected_profile.width
            updated_settings["height"] = selected_profile.height
            updated_settings["fps"] = (
                selected_profile.fps or camera_settings.fps or 30.0
            )
            updated_settings["pixel_format"] = (
                selected_profile.pixel_format or camera_settings.pixel_format
            )
            updated_settings["media_type"] = (
                selected_profile.media_type or camera_settings.media_type
            )
        elif isinstance(selected_profile, DeviceStepwise):
            width = camera_settings.width or selected_profile.min_width
            height = camera_settings.height or selected_profile.min_height
            fps = camera_settings.fps or selected_profile.max_fps
            updated_settings["width"] = int(width)
            updated_settings["height"] = int(height)
            updated_settings["fps"] = min(
                max(float(fps), float(selected_profile.min_fps)),
                float(selected_profile.max_fps),
            )
            updated_settings["pixel_format"] = (
                selected_profile.pixel_format or camera_settings.pixel_format
            )
            updated_settings["media_type"] = (
                selected_profile.media_type or camera_settings.media_type
            )
        else:
            updated_settings["width"] = camera_settings.width or 640
            updated_settings["height"] = camera_settings.height or 480
            updated_settings["fps"] = camera_settings.fps or 30.0

        try:
            return str(av_device.localizedName()), CameraSettings(**updated_settings)
        except ValidationError as error:
            raise CameraDeviceError(
                f"Camera mode cannot use these controls: {error}"
            ) from error
