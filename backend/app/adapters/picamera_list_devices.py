from typing import List

from app.schemas.camera import DeviceStepwise
from picamera2 import Picamera2


def detect_cameras() -> List[DeviceStepwise]:
    devices = Picamera2.global_camera_info()
    detected = []

    for i, device in enumerate(devices):
        try:
            picam2 = Picamera2(i)
            sensor_modes = picam2.sensor_modes

            sizes = [
                mode.get("size")
                for mode in sensor_modes
                if isinstance(mode.get("size"), tuple)
            ]
            all_fps = [mode.get("fps") for mode in sensor_modes if mode.get]
            widths = [size[0] for size in sizes if size]
            heights = [size[1] for size in sizes if size]

            if heights and widths and all_fps:
                min_width = min(widths)
                max_width = max(widths)
                min_height = min(heights)
                max_height = max(heights)
                min_fps = min(all_fps)
                max_fps = max(all_fps)

                detected.append(
                    DeviceStepwise(
                        device=device["Id"],
                        name=device["Model"],
                        api="picamera2",
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
                    )
                )
        except Exception:
            pass

    return detected


def global_camera_info() -> list:
    """Return Id string and Model name for all attached cameras, one dict per camera.

    Ordered correctly by camera number. Also return the location and rotation
    of the camera when known, as these may help distinguish which is which.
    """

    def describe_camera(cam, num: int):
        items = cam.properties.items()
        print(f"info items for {num}={items}")
        info = {k.name: v for k, v in cam.properties.items()}
        print(f"info for {num}={items}")
        info["Id"] = cam.id
        info["Num"] = num
        return info

    cameras = [
        describe_camera(cam, i) for i, cam in enumerate(Picamera2._cm.cms.cameras)
    ]
    # Sort alphabetically so they are deterministic, but send USB cams to the back of the class.
    return sorted(
        cameras, key=lambda cam: ("/usb" not in cam["Id"], cam["Id"]), reverse=True
    )


global_camera_info()

for camera in detect_cameras():
    print(camera.model_dump_json(indent=4))
