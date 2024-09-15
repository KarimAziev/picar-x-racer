import asyncio
import os

import cv2
import numpy as np
from app.util.logger import Logger

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

    status = cv2.imwrite(os.path.join(path, photo_name), img)

    return status


def height_to_width(height: int, target_width: int, target_height: int):
    aspect_ratio = target_width / target_height
    width = aspect_ratio * height
    return int(width)
