from app.util.object_detection import (
    perform_cat_detection,
    perform_detection,
    perform_person_detection,
)

detectors = {
    "cat": perform_cat_detection,
    "person": perform_person_detection,
    "all": perform_detection,
}
