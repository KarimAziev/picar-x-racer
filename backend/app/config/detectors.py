from app.util.detect_cat import detect_cat_extended_faces, detect_cat_faces
from app.util.detect_colors import (
    highlight_black_areas,
    highlight_blue_areas,
    highlight_red_areas,
    highlight_white_areas,
)
from app.util.detect_human import detect_full_body_faces, detect_human_faces
from app.util.mobile_net import detect_objects_with_mobilenet

detectors = {
    "mobile_net": detect_objects_with_mobilenet,
    "cat": detect_cat_faces,
    "cat_extended": detect_cat_extended_faces,
    "human_body": detect_full_body_faces,
    "human_face": detect_human_faces,
    "highlight_black_areas": highlight_black_areas,
    "highlight_blue_areas": highlight_blue_areas,
    "highlight_white_areas": highlight_white_areas,
    "highlight_red_areas": highlight_red_areas,
}
