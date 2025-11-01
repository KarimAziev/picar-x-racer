import math
import threading
import time
from functools import lru_cache
from typing import Dict, List, Optional, Union

from app.core.logger import Logger
from app.schemas.camera import DeviceStepwise, DeviceType
from app.services.camera.v4l2_service import VideoDeviceABC
from app.types.picamera_types import GlobalCameraInfo

_log = Logger(name=__name__)


PIXEL_FORMATS_TO_PICAMERA2_MAP: Dict[str, str] = {
    "I420": "YUV420",
    # "YV12": "YVU420",
    "RGBx": "XRGB8888",
    "RGB": "RGB888",
    "BGR": "BGR888",
    "BGRx": "XBGR8888",
}

PICAMERA2_TO_PIXEL_FORMATS_MAP: Dict[str, str] = {
    v: k for k, v in PIXEL_FORMATS_TO_PICAMERA2_MAP.items()
}

PICAMERA_TO_PIXEL_FORMATS_KEYS = PIXEL_FORMATS_TO_PICAMERA2_MAP.keys()

_picamera2_lock = threading.Lock()


class PicameraService(VideoDeviceABC):
    def list_video_devices(self) -> List[DeviceType]:
        return self._list_video_devices()

    @lru_cache()
    def _list_video_devices(self) -> List[DeviceType]:
        with _picamera2_lock:
            try:
                from picamera2 import Picamera2
            except ImportError:
                _log.warning("Picamera2 is not installed")
                return []
            except Exception:
                _log.warning(
                    "Unexpected error while importing Picamera2", exc_info=True
                )
                return []

            _log.info("Listing picamera2 devices")

            try:
                devices: List[GlobalCameraInfo] = Picamera2.global_camera_info()
            except Exception:
                _log.error("Failed to retrieve Picamera devices:", exc_info=True)
                return []

        try:
            devices: List[GlobalCameraInfo] = Picamera2.global_camera_info()
            detected: List[DeviceType] = []

            for device in devices:
                picam2: Optional[Picamera2] = None
                try:

                    device_path = device.get("Id")
                    device_num = device.get("Num")
                    device_model = device.get("Model")
                    device_rotation = device.get("Rotation")
                    device_location = device.get("Location")

                    _log.info(
                        f"Probing picamera2 device {device_num} ({device_path}) "
                        f"model={device_model}, "
                        f"rotation={device_rotation}, "
                        f"location={device_location}"
                    )

                    time.sleep(0.1)

                    with _picamera2_lock:
                        try:
                            picam2 = Picamera2(device_num)
                            sensor_modes = picam2.sensor_modes

                        finally:
                            if picam2 is not None:
                                try:
                                    picam2.close()
                                except Exception as e:
                                    _log.error(
                                        "Failed to close picamera2 instance: %s", e
                                    )
                                picam2 = None

                    sizes = [
                        mode.get("size")
                        for mode in sensor_modes
                        if isinstance(mode.get("size"), tuple)
                        and len(mode.get("size", [])) == 2
                    ]
                    min_fps: Union[float, int, None] = None
                    max_fps: Union[float, int, None] = None

                    for mode in sensor_modes:
                        fps = mode.get("fps")
                        if isinstance(fps, float) or isinstance(fps, int):
                            min_fps = (
                                fps
                                if min_fps is None
                                else fps if fps < min_fps else min_fps
                            )
                            max_fps = (
                                fps
                                if max_fps is None
                                else fps if fps > max_fps else max_fps
                            )

                    widths: List[float] = [size[0] for size in sizes if size]
                    heights: List[float] = [size[1] for size in sizes if size]

                    if heights and widths and min_fps and max_fps:
                        min_width = min(320, int(min(widths)))
                        max_width = int(max(widths))
                        min_height = min(240, int(min(heights)))
                        max_height = int(max(heights))
                        min_fps = math.ceil(min_fps)
                        max_fps = round(max_fps)
                        api = "picamera2"
                        device_full = f"{api}:{device_path}"

                        formats = [
                            DeviceStepwise(
                                device=device_full,
                                name=device_model,
                                api=api,
                                height_step=2,
                                width_step=2,
                                fps_step=1,
                                pixel_format=pixel_fmt,
                                min_width=min_width,
                                max_width=max_width,
                                min_height=min_height,
                                max_height=max_height,
                                min_fps=min_fps,
                                max_fps=max_fps,
                                path=device_path,
                            )
                            for pixel_fmt in PICAMERA_TO_PIXEL_FORMATS_KEYS
                        ]

                        detected.append(
                            DeviceStepwise(
                                device=device_full,
                                name=device_model,
                                api=api,
                                height_step=2,
                                width_step=2,
                                fps_step=1,
                                pixel_format=None,
                                min_width=min_width,
                                max_width=max_width,
                                min_height=min_height,
                                max_height=max_height,
                                min_fps=min_fps,
                                max_fps=max_fps,
                                path=device_path,
                            )
                        )
                        detected.extend(formats)
                except RuntimeError as e:
                    _log.error(
                        "Picamera runtime error for device %d: %s, %s",
                        device.get("Num"),
                        device.get("Model"),
                        e,
                    )
                except Exception:
                    _log.error(
                        "Unexpected Picamera error for device %d:",
                        device.get("Num"),
                        device.get("Model"),
                        exc_info=True,
                    )

            return detected
        except Exception as e:
            _log.error("Failed to retrieve Picamera devices: %s")
            return []


if __name__ == "__main__":
    service = PicameraService()
    result = service.list_video_devices()
    _log.info(f"picamera2 devices={result}")
