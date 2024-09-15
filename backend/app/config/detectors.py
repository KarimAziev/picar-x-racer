from app.util.object_detection import (
    perform_cat_detection,
    perform_detection,
    perform_person_detection,
)

detectors = {
    "all": perform_detection,
    "cat": perform_cat_detection,
    "person": perform_person_detection,
}
