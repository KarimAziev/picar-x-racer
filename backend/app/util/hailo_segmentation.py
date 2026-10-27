"""Decode Hailo Model Zoo YOLOv8 instance segmentation tensors."""

from typing import Dict, List, Tuple

import cv2
import numpy as np


def decode_yolov8_segmentation(
    outputs: Dict[str, np.ndarray],
    input_shape: Tuple[int, ...],
    confidence: float,
    iou: float,
    max_detections: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[np.ndarray]]:
    """Return input-pixel boxes, scores, class IDs and one polygon per instance.

    The HEF supplies sigmoid class scores, 16-bin box distributions, 32 mask
    coefficients per anchor and a quarter-resolution mask prototype tensor.
    """
    height, width = input_shape[:2]
    layers = {value.shape: value for value in outputs.values()}
    prototypes = layers[(height // 4, width // 4, 32)]
    boxes, scores, classes, coefficients = [], [], [], []
    for stride in (8, 16, 32):
        h, w = height // stride, width // stride
        logits = layers[(h, w, 64)].reshape(-1, 4, 16)
        class_scores = layers[(h, w, 80)].reshape(-1, 80)
        class_ids = class_scores.argmax(axis=1)
        best_scores = class_scores.max(axis=1)
        keep = best_scores >= confidence
        if not np.any(keep):
            continue
        distributions = logits[keep]
        probabilities = np.exp(
            distributions - distributions.max(axis=-1, keepdims=True)
        )
        probabilities /= probabilities.sum(axis=-1, keepdims=True)
        distances = (probabilities * np.arange(16)).sum(axis=-1) * stride
        x, y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
        centers = np.stack((x, y), axis=-1).reshape(-1, 2)[keep] * stride
        boxes.append(
            np.concatenate(
                (centers - distances[:, :2], centers + distances[:, 2:]), axis=1
            )
        )
        scores.append(best_scores[keep])
        classes.append(class_ids[keep])
        coefficients.append(layers[(h, w, 32)].reshape(-1, 32)[keep])
    if not boxes:
        return np.empty((0, 4)), np.empty(0), np.empty(0, dtype=int), []

    all_boxes, all_scores = np.concatenate(boxes), np.concatenate(scores)
    all_classes, all_coefficients = np.concatenate(classes), np.concatenate(
        coefficients
    )
    xywh = all_boxes.copy()
    xywh[:, 2:] -= xywh[:, :2]
    selected = cv2.dnn.NMSBoxesBatched(
        xywh.tolist(), all_scores.tolist(), all_classes.tolist(), confidence, iou
    )
    selected = np.asarray(selected, dtype=int).reshape(-1)[:max_detections]
    polygons: List[np.ndarray] = []
    for index in selected:
        # A zero logit is a 0.5 mask probability.
        mask = (prototypes @ all_coefficients[index] > 0).astype(np.uint8)
        x1, y1, x2, y2 = np.rint(all_boxes[index] / 4).astype(int)
        x1, x2 = np.clip([x1, x2], 0, mask.shape[1])
        y1, y2 = np.clip([y1, y2], 0, mask.shape[0])
        cropped = np.zeros_like(mask)
        cropped[y1:y2, x1:x2] = mask[y1:y2, x1:x2]
        contours, _ = cv2.findContours(
            cropped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        polygon = (
            max(contours, key=cv2.contourArea).reshape(-1, 2).astype(np.float32) * 4
            if contours
            else np.empty((0, 2), dtype=np.float32)
        )
        polygons.append(polygon)
    return all_boxes[selected], all_scores[selected], all_classes[selected], polygons
