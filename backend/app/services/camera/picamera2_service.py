import math
from functools import lru_cache
from typing import Dict, List, Tuple

from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.schemas.camera import DeviceStepwise, DeviceType
from app.services.camera.v4l2_service import VideoDeviceABC
from app.types.picamera_types import GlobalCameraInfo

logger = Logger(name=__name__)


PIXEL_FORMATS_TO_PICAMERA2_MAP: Dict[str, str] = {
    "I420": "YUV420",
    "YV12": "YVU420",
    "RGBx": "XRGB8888",
    "RGB": "RGB888",
    "BGR": "BGR888",
    "BGRx": "XBGR8888",
}

PICAMERA2_TO_PIXEL_FORMATS_MAP: Dict[str, str] = {
    v: k for k, v in PIXEL_FORMATS_TO_PICAMERA2_MAP.items()
}


class PicameraService(VideoDeviceABC, metaclass=SingletonMeta):
    def list_video_devices(self) -> List[DeviceType]:
        return self._list_video_devices()

    @lru_cache()
    def _list_video_devices(self) -> List[DeviceType]:
        try:
            from picamera2 import Picamera2
        except Exception:
            logger.warning("Picamera2 is not installed")
            return []

        logger.info("Listing picamera2 devices")

        try:
            devices: List[GlobalCameraInfo] = Picamera2.global_camera_info()
            detected = []

            for i, device in enumerate(devices):
                picam2 = None
                try:
                    picam2 = Picamera2(i)
                    sensor_modes = picam2.sensor_modes

                    sizes: List[Tuple[float, float]] = [
                        mode.get("size")
                        for mode in sensor_modes
                        if isinstance(mode.get("size"), tuple)
                        and len(mode.get("size")) == 2
                    ]
                    all_fps: List[float] = [
                        mode.get("fps") for mode in sensor_modes if mode.get("fps")
                    ]
                    widths: List[float] = [size[0] for size in sizes if size]
                    heights: List[float] = [size[1] for size in sizes if size]

                    if heights and widths and all_fps:
                        min_width = min(320, int(min(widths)))
                        max_width = int(max(widths))
                        min_height = min(240, int(min(heights)))
                        max_height = int(max(heights))
                        min_fps = math.ceil(min(all_fps))
                        max_fps = round(max(all_fps))
                        device_path: str = device.get("Id")
                        api = "picamera2"
                        device_full = f"{api}:{device_path}"
                        name = device.get("Model")

                        formats = [
                            DeviceStepwise(
                                device=device_full,
                                name=name,
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
                            for pixel_fmt in PIXEL_FORMATS_TO_PICAMERA2_MAP.keys()
                        ]

                        detected.append(
                            DeviceStepwise(
                                device=device_full,
                                name=name,
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
                except Exception:
                    pass
                finally:
                    if picam2 is not None:
                        picam2.close()

            return detected
        except Exception:
            logger.warning("Picamera2 is not installed")
            return []


if __name__ == "__main__":
    service = PicameraService()
    result = service.list_video_devices()
    logger.info(f"picamera2 devices={result}")
