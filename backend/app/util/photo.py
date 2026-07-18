import asyncio
import os
from typing import Optional, Union

import cv2
import numpy as np
from app.core.logger import Logger
from app.schemas.detection import DetectionSettings
from app.schemas.stream import ImageRotation
from app.types.detection import DetectionQueueData, DetectionResultData
from app.util.overlay_detecton import overlay_detection

logger = Logger(__name__)


async def capture_photo(img: np.ndarray, photo_name: str, path: str) -> bool:
    """
    Asynchronously take a photo and save it to the specified path.

    Args:
        img (np.ndarray): Image data in numpy array format.
        photo_name (str): Name of the photo file.
        path (str): Directory path to save the photo.

    Returns:
        bool: Status indicating success or failure of taking the photo.
    """
    logger.info(f"Taking photo '{photo_name}' at path {path}")
    if not os.path.exists(path):
        os.makedirs(name=path, mode=0o751, exist_ok=True)
        await asyncio.sleep(0.01)

    status = await asyncio.to_thread(cv2.imwrite, os.path.join(path, photo_name), img)

    return status


def round_up_to_multiple_of(val: Union[int, float], multiple: int) -> Union[int, float]:
    return ((val + multiple - 1) // multiple) * multiple


def height_to_width(
    height: int,
    target_width: int,
    target_height: int,
    round_up_to_multiple: Optional[int] = None,
) -> int:
    aspect_ratio = target_width / target_height
    width = aspect_ratio * height
    rounded_width = (
        round_up_to_multiple_of(width, round_up_to_multiple)
        if round_up_to_multiple is not None
        else width
    )
    return int(rounded_width)


def width_to_height(
    width: int,
    target_width: int,
    target_height: int,
    round_up_to_multiple: Optional[int] = None,
) -> int:
    aspect_ratio = target_height / target_width
    height = aspect_ratio * width

    rounded_height = (
        round_up_to_multiple_of(height, round_up_to_multiple)
        if round_up_to_multiple is not None
        else height
    )
    return int(rounded_height)


def should_render_detection_overlay(
    frame_timestamp: Optional[float],
    detection_timestamp: Optional[float],
    overlay_draw_threshold: float,
) -> bool:
    if frame_timestamp is None or detection_timestamp is None:
        return False
    return frame_timestamp - detection_timestamp <= overlay_draw_threshold


def prepare_photo_frame(
    frame: np.ndarray,
    rotation: ImageRotation,
    detection_settings: Optional[DetectionSettings] = None,
    detection_state: Optional[Union[DetectionQueueData, DetectionResultData]] = None,
    frame_timestamp: Optional[float] = None,
    render_detection_overlay: bool = True,
) -> np.ndarray:
    result = prepare_detection_overlay_frame(
        frame=frame,
        detection_settings=detection_settings,
        detection_state=detection_state,
        frame_timestamp=frame_timestamp,
        render_detection_overlay=render_detection_overlay,
    )

    if rotation == ImageRotation.rotate_90:
        return cv2.rotate(np.ascontiguousarray(result), cv2.ROTATE_90_CLOCKWISE)
    if rotation == ImageRotation.rotate_180:
        return cv2.rotate(np.ascontiguousarray(result), cv2.ROTATE_180)
    if rotation == ImageRotation.rotate_270:
        return cv2.rotate(np.ascontiguousarray(result), cv2.ROTATE_90_COUNTERCLOCKWISE)
    return result


def prepare_detection_overlay_frame(
    frame: np.ndarray,
    detection_settings: Optional[DetectionSettings] = None,
    detection_state: Optional[Union[DetectionQueueData, DetectionResultData]] = None,
    frame_timestamp: Optional[float] = None,
    render_detection_overlay: bool = True,
) -> np.ndarray:
    result = frame.copy()

    if not render_detection_overlay:
        return result

    if detection_settings and detection_settings.active and detection_state:
        detection_result = detection_state.get("detection_result") or []
        semantic_mask = detection_state.get("semantic_mask")
        detection_timestamp = detection_state.get("timestamp")
        if (detection_result or semantic_mask) and should_render_detection_overlay(
            frame_timestamp,
            detection_timestamp,
            detection_settings.overlay_draw_threshold,
        ):
            result = overlay_detection(
                result,
                detection_result,
                detection_settings.overlay_style,
                semantic_mask,
            )

    return result
