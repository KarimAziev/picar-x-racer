
import cv2
import numpy as np
import torchvision.transforms as T

from app.util.logger import Logger
from app.config.yolo_model import yolo_model, device

logger = Logger(__name__)

def detect_cat_extended_faces(frame: np.ndarray) -> np.ndarray:
    try:
        border_color = (191, 255, 0)

        resized_frame = cv2.resize(frame, (320, 320))

        transform = T.ToTensor()
        tensor_frame = transform(resized_frame).unsqueeze(0).to(device)

        results = yolo_model(tensor_frame)[0]

        scale_x = frame.shape[1] / resized_frame.shape[1]
        scale_y = frame.shape[0] / resized_frame.shape[0]

        for result in results.cpu().numpy():
            x1, y1, x2, y2 = result[:4]
            conf = result[4]
            class_scores = result[5:]
            cls = np.argmax(class_scores)
            cls_name = yolo_model.names[cls]

            if cls_name == "cat" and conf > 0.25:  # confidence threshold
                x1, y1, x2, y2 = map(
                    int, [x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]
                )
                frame = cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 2)
                frame = cv2.putText(
                    frame,
                    f"{cls_name} {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    border_color,
                    2,
                )
    except Exception as e:

        logger.error(f"Error in detect_cat_faces: {e}")

    return frame


def detect_cat_faces(frame: np.ndarray) -> np.ndarray:
    border_color = (191, 255, 0)

    reduced_frame = cv2.resize(frame, (320, 240))
    results = yolo_model(reduced_frame)
    scale_x = frame.shape[1] / reduced_frame.shape[1]
    scale_y = frame.shape[0] / reduced_frame.shape[0]

    for result in results.xyxy[0]:
        x1, y1, x2, y2, conf, cls = result
        if yolo_model.names[int(cls)] == "cat":
            x1, y1, x2, y2 = map(
                int, [x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]
            )
            frame = cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 2)
            frame = cv2.putText(
                frame,
                f"{yolo_model.names[int(cls)]} {conf:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                border_color,
                2,
            )
    return frame