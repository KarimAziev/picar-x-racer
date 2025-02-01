import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.core.logger import Logger
from app.schemas.camera import DeviceStepwise, DiscreteDevice

logger = Logger(__name__)


class GStreamerParser:
    GROUP_TYPE_PATTERN = r"^(name|caps|properties)\s*:\s*(.*)?$"
    MEDIA_TYPE_REGEX = r"^(?:[a-zA-Z0-9]+/[a-zA-Z0-9\+\.\-]+)$"

    def __init__(self):
        self.current_parser: Optional[Callable[[str], None]] = None
        self.name: Optional[str] = None
        self.props: Dict[str, Any] = {}
        self.caps: List[Dict[str, Any]] = []
        self.result: List[Union[DiscreteDevice, DeviceStepwise]] = []

    @staticmethod
    def parse_device_path(input_string: str) -> Tuple[Optional[str], str]:
        match = re.match(r"([^:]+):/(.+)", input_string)
        if match:
            part1 = match.group(1)
            part2 = f"/{match.group(2)}"
            return part1, part2
        else:
            return None, input_string

    def parse(self, output: str) -> List[Union[DiscreteDevice, DeviceStepwise]]:
        lines = output.splitlines()

        for line in lines:
            self._process_line(line)

        self._finalize_group()
        return self.result

    def _process_line(self, line: str) -> None:
        line = line.strip()

        if not line:
            return

        if match := re.match(self.GROUP_TYPE_PATTERN, line):
            subtype = match.group(1)
            rest_of_string = match.group(2).strip()
            self.current_parser = None

            match subtype:
                case "name":
                    self._finalize_group()
                    self.name = rest_of_string
                case "caps":
                    self.current_parser = self._parse_caps_line
                    self.caps = []
                    self.current_parser(rest_of_string)
                case "properties":
                    self.current_parser = self._parse_props_line
                    self.props = {}
                    self.current_parser(rest_of_string)
        elif self.current_parser:
            self.current_parser(line)

    @staticmethod
    def _replace_framerate(match: re.Match[str]) -> str:
        fractions = re.findall(r"\(fraction\)\s*([0-9]+/[0-9]+)", match.group(0))
        return "[ " + ", ".join(fractions) + " ]"

    @staticmethod
    def _normalize_framerate(line: str) -> str:
        pattern = r"\{\s*(?:\(fraction\)\s*([0-9]+/[0-9]+),?\s*)+\}"
        return re.sub(pattern, GStreamerParser._replace_framerate, line)

    def _parse_caps_line(self, line: str) -> None:
        line = self._normalize_framerate(line)

        line = re.sub(r"=\[[ ]*([0-9/]+)(,[ ]*)([0-9/]+)", r"=[\1-\3", line)
        parts = [item.strip() for item in line.split(",") if item.strip()]
        cap: Dict[str, Any] = {}
        for item in parts:
            if re.match(self.MEDIA_TYPE_REGEX, item):
                cap["media_type"] = item
            else:
                parts = [i.strip() for i in item.split("=") if i.strip()]
                if len(parts) >= 2:
                    label = parts[0]
                    value = "=".join(parts[1:])
                    if value.startswith("["):
                        value = [
                            i.strip() for i in value.strip("[]").split("-") if i.strip()
                        ]

                    match label:
                        case "format":
                            cap["pixel_format"] = value
                        case "width":
                            if value and isinstance(value, str):
                                value = int(value)
                                cap["width"] = value
                            elif isinstance(value, list) and len(value) == 2:
                                cap["min_width"] = int(value[0])
                                cap["max_width"] = int(value[1])
                                cap["width_step"] = 2
                        case "height":
                            if value and isinstance(value, str):
                                value = int(value)
                                cap["height"] = value
                            elif isinstance(value, list) and len(value) == 2:
                                cap["height_step"] = 2
                                cap["min_height"] = int(value[0])
                                cap["max_height"] = int(value[1])

                        case "framerate":
                            if value and isinstance(value, str):
                                value = value.split("/")[0]
                                value = int(value)
                                cap["fps"] = value
                            elif isinstance(value, list) and len(value) == 2:
                                cap["min_fps"] = int(value[0].split("/")[0])
                                cap["max_fps"] = int(value[1].split("/")[0])

        if cap.keys():
            if cap.get("min_fps") or cap.get("max_fps"):
                if not cap.get("min_width") or not cap.get("min_height"):
                    min_fps = cap.get("min_fps")
                    max_fps = cap.get("max_fps")
                    print("max_fps", max_fps)
                    cap.pop("min_fps")
                    cap.pop("max_fps")

                    self.caps.extend([{**cap, "fps": min_fps}, {**cap, "fps": max_fps}])
                else:
                    self.caps.append(cap)
            else:
                self.caps.append(cap)

    def _parse_props_line(self, line: str):
        pattern = r"^[^\s]+[\s]="

        parts = (
            [item.strip() for item in line.split("=") if item.strip()]
            if re.match(pattern, line)
            else []
        )
        if len(parts) >= 2:
            label = parts[0]
            value = "=".join(parts[1:])
            self.props[label] = value

    def _finalize_group(self):
        obj_path = self.props.get("object.path")
        if self.caps and self.name and obj_path:
            api, path = self.parse_device_path(obj_path)

            for item in self.caps:
                width = item.get("width")
                height = item.get("height")

                min_width = item.get("min_width")
                min_height = item.get("min_height")

                max_height = item.get("max_height")
                max_width = item.get("max_width")

                merged_data = {
                    **item,
                    "name": self.name,
                    "device": obj_path,
                    "api": api,
                    "path": path,
                }

                data = (
                    DiscreteDevice(**merged_data)
                    if isinstance(width, int) and isinstance(height, int)
                    else (
                        DeviceStepwise(**merged_data)
                        if isinstance(min_height, int)
                        and isinstance(min_width, int)
                        and isinstance(max_height, int)
                        and isinstance(max_width, int)
                        else None
                    )
                )

                if not data:
                    continue

                self.result.append(data)

            self.caps = []
            self.props = {}
            self.current_parser = None
