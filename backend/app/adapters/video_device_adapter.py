from typing import Any, Dict, List, Optional, Tuple

import cv2
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.core.v4l2_parser import V4L2FormatParser
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.managers.gstreamer_manager import GstreamerManager
from app.managers.v4l2_manager import V4L2
from app.schemas.camera import CameraSettings
from app.util.device import try_video_path

logger = Logger(name=__name__)


class VideoDeviceAdapater(metaclass=SingletonMeta):
    """
    A singleton class responsible for managing video capturing devices.
    """

    @staticmethod
    def find_device_info(device: str) -> Optional[str]:
        """
        Finds the device info of a specific camera device from the list of available camera devices.

        Searches for the given device in the list of available camera devices and
        returns its associated information (e.g., device path and category).

        Args:
            device: The path to the camera device (e.g., `/dev/video0`).

        Returns:
            The device path.
        """
        devices = (
            V4L2.list_camera_device_names()
            + GstreamerManager.list_camera_device_names()
        )
        for device_path in devices:
            if device_path == device:
                return device_path

    @staticmethod
    def try_device_props(
        device: str, camera_settings: CameraSettings
    ) -> Optional[Tuple[cv2.VideoCapture, CameraSettings]]:
        if camera_settings.use_gstreamer:
            pipeline = GstreamerManager.setup_pipeline(
                device,
                width=camera_settings.width,
                height=camera_settings.height,
                fps=camera_settings.fps,
                pixel_format=camera_settings.pixel_format,
                media_type=camera_settings.media_type,
            )
            cap = try_video_path(pipeline, backend=cv2.CAP_GSTREAMER)
            if cap is None:
                return None
            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
            }
        else:
            _, device_path = GStreamerParser.parse_device_path(device)
            cap = try_video_path(
                device_path,
                backend=cv2.CAP_V4L2,
                width=camera_settings.width,
                height=camera_settings.height,
                fps=camera_settings.fps,
                pixel_format=camera_settings.pixel_format,
            )
            if cap is None:
                return None
            width, height, fps = (
                cap.get(x)
                for x in (
                    cv2.CAP_PROP_FRAME_WIDTH,
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    cv2.CAP_PROP_FPS,
                )
            )

            data = V4L2.video_capture_format(device_path) or {}

            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
                "width": int(width),
                "height": int(height),
                "fps": int(fps),
                "pixel_format": data.get("pixel_format", camera_settings.pixel_format),
            }

        return cap, CameraSettings(**updated_settings)

    @staticmethod
    def flattenize_children(items: List[Dict[str, Any]]):
        stack = items.copy()
        result: List[Dict[str, Any]] = []
        while stack:
            item = stack.pop()
            children = item.get("children")
            if children:
                result.extend(children.copy())
        return result

    @staticmethod
    def merge_devices(
        items: List[Dict[str, Any]], items_to_exclude: List[Dict[str, Any]]
    ):
        flattenized = VideoDeviceAdapater.flattenize_children(items_to_exclude)
        video_paths = [item.get("path") for item in items_to_exclude if item]
        new_devices = []
        devices_to_merge = {}
        merged_result = []

        keys_to_exclude = [
            f"{item.get('path')}:{item.get('pixel_format')}"
            for item in flattenized
            if item.get("pixel_format")
        ]

        def filter_child(item: Dict[str, Any]):
            if not item.get("children"):
                key = f"{item.get('device')}:{item.get('pixel_format')}"
                if key not in keys_to_exclude:
                    return item
            else:
                children = item.get("children", [])
                filtered_children = []
                for child in children:
                    if filter_child(child):
                        filtered_children.append(child)
                if len(filtered_children) > 0:
                    return {**item, "children": filtered_children}

        for device in items:
            key = device.get("key")
            if key not in video_paths:
                new_devices.append(device)
            else:
                filtered_device = filter_child(device)
                if filtered_device:
                    devices_to_merge[key] = filtered_device.get("children")

        for item in items_to_exclude:
            path = item.get("path")
            new_children = devices_to_merge.get(path)
            if new_children:
                data = {**item, "children": item.get("children") + new_children}
                merged_result.append(data)
            else:
                merged_result.append(item)

        return merged_result + new_devices

    @staticmethod
    def list_devices():
        v4l2_devices = V4L2.list_video_devices_with_formats()
        gstreamer_devices = (
            GstreamerManager.list_video_devices_with_formats()
            if GstreamerManager.gstreamer_available()
            else None
        )
        if gstreamer_devices is None:
            return v4l2_devices

        results = []
        gstreamer_devices_paths: List[str] = []

        for item in gstreamer_devices:
            path = item.get("path")
            if not isinstance(path, str):
                continue
            if item.get("api") != "v4l2":
                results.append(item)
                gstreamer_devices_paths.append(path)
            else:
                children: List[Dict[str, Any]] = item.get("children", [])
                filtered_children: List[Dict[str, Any]] = []
                for child in children:
                    subchildren = child.get("children")
                    if isinstance(subchildren, list) and len(subchildren) == 0:
                        continue
                    subchild = (
                        subchildren[0] if isinstance(subchildren, list) else subchildren
                    )

                    min_width = (
                        subchild.get("min_width")
                        if subchild is not None
                        else child.get("min_width")
                    )
                    min_height = (
                        subchild.get("min_height")
                        if subchild is not None
                        else child.get("min_height")
                    )
                    pixel_format = (
                        subchild.get("pixel_format")
                        if subchild is not None
                        else child.get("pixel_format")
                    )
                    if pixel_format and path and min_width and min_height:
                        if V4L2FormatParser.get_fps_intervals(
                            device=path,
                            width=min_width,
                            height=min_height,
                            pixel_format=pixel_format,
                        ):
                            filtered_children.append(child)
                    elif pixel_format:
                        filtered_children.append(child)

                if filtered_children:
                    item["children"] = filtered_children
                    results.append(item)
                    gstreamer_devices_paths.append(path)

        return VideoDeviceAdapater.merge_devices(v4l2_devices, results.copy())

    def setup_video_capture(
        self, camera_settings: CameraSettings
    ) -> Tuple[cv2.VideoCapture, CameraSettings]:
        if camera_settings.device is not None:
            video_device = self.find_device_info(camera_settings.device)
            if video_device is None:
                raise CameraNotFoundError("Video device is not available")
            else:
                device_path = video_device
                result = self.try_device_props(device_path, camera_settings)
                if result is None:
                    raise CameraDeviceError("Video capture failed")
                else:
                    return result
        else:
            devices = (
                V4L2.list_camera_device_names()
                + GstreamerManager.list_camera_device_names()
            )
            result = None
            if len(devices) > 0:
                result = self.try_device_props(devices[0], camera_settings)

            if result is None:
                raise CameraNotFoundError("Couldn't find video device")
            else:
                return result
