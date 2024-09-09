import cv2
import numpy as np
from app.config.paths import (
    HUMAN_FACE_CASCADE_PATH,
    HUMAN_FULL_BODY_CASCADE_PATH,
)
from app.util.logger import Logger


logger = Logger(__name__)


human_face_cascade = cv2.CascadeClassifier(HUMAN_FACE_CASCADE_PATH)
human_full_body_cascade = cv2.CascadeClassifier(HUMAN_FULL_BODY_CASCADE_PATH)

def detect_human_faces(frame: np.ndarray) -> np.ndarray:
    border_color = (191, 255, 0)
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    human_faces = human_face_cascade.detectMultiScale(
        gray_frame, scaleFactor=1.1, minNeighbors=5
    )

    for x, y, w, h in human_faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), border_color, 2)
    return frame


def detect_full_body_faces(frame: np.ndarray) -> np.ndarray:
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    human_full_bodies = human_full_body_cascade.detectMultiScale(
        gray_frame, scaleFactor=1.1, minNeighbors=5
    )
    for x, y, w, h in human_full_bodies:
        frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (191, 255, 0), 2)
    return frame