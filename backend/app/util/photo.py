import asyncio
import os
from typing import Optional

import cv2
import numpy as np
from app.core.logger import Logger

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


def round_up_to_multiple_of(val: int | float, multiple: int):
    return ((val + multiple - 1) // multiple) * multiple


def height_to_width(
    height: int,
    target_width: int,
    target_height: int,
    round_up_to_multiple: Optional[int] = None,
):
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
):
    aspect_ratio = target_height / target_width
    height = aspect_ratio * width

    rounded_height = (
        round_up_to_multiple_of(height, round_up_to_multiple)
        if round_up_to_multiple is not None
        else height
    )
    return int(rounded_height)
