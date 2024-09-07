
import cv2
import torch
from app.config.paths import (
    HUMAN_FACE_CASCADE_PATH,
    HUMAN_FULL_BODY_CASCADE_PATH,
)
from PIL import ImageFont
from app.util.logger import Logger
from app.config.paths import (
    FONT_PATH,
)

logger = Logger(__name__)


human_face_cascade = cv2.CascadeClassifier(HUMAN_FACE_CASCADE_PATH)
human_full_body_cascade = cv2.CascadeClassifier(HUMAN_FULL_BODY_CASCADE_PATH)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5n', pretrained=True)
font = ImageFont.truetype(FONT_PATH, 24)