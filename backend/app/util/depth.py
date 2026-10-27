"""Compact relative-depth maps and their camera overlays."""

import base64
from typing import Optional

import cv2
import numpy as np

from app.types.detection import DepthMapData


def encode_depth_map(depth: np.ndarray, max_side: int = 256) -> DepthMapData:
    """Encode relative depth as base64 uint8 pixels, with near=0 and far=255."""
    values = np.nan_to_num(
        np.asarray(depth, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0
    )
    height, width = values.shape
    scale = min(1.0, max_side / max(height, width))
    width, height = max(1, round(width * scale)), max(1, round(height * scale))
    values = cv2.resize(values, (width, height), interpolation=cv2.INTER_LINEAR)
    near, far = float(values.min()), float(values.max())
    pixels = np.zeros_like(values, dtype=np.uint8)
    if far > near:
        pixels = np.clip((values - near) * 255 / (far - near), 0, 255).astype(np.uint8)
    return {
        "width": width,
        "height": height,
        "data": base64.b64encode(pixels.tobytes()).decode("ascii"),
        "near": near,
        "far": far,
        "units": "relative",
    }


def draw_depth_map(frame: np.ndarray, depth: Optional[DepthMapData]) -> np.ndarray:
    """Blend near-red/far-blue relative depth over a BGR camera frame."""
    if depth is None:
        return frame
    values = np.frombuffer(base64.b64decode(depth["data"]), dtype=np.uint8).reshape(
        depth["height"], depth["width"]
    )
    v = values.astype(np.int16)
    colors = np.stack((v, 255 - np.abs(2 * v - 255), 255 - v), axis=-1).astype(np.uint8)
    colors = cv2.resize(
        colors, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_LINEAR
    )
    return cv2.addWeighted(frame, 0.25, colors, 0.75, 0)
