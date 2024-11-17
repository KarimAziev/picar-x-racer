import os

from app.config.paths import DATA_DIR
from app.util.file_util import get_directory_structure
from app.util.google_coral import is_google_coral_connected

yolo_descriptions = {
    'yolov5nu.pt': 'Nano version of YOLOv5 for balanced speed and accuracy in resource-constrained devices.',
    'yolov5su.pt': 'Small variant of YOLOv5 offering enhanced accuracy with moderate speed trade-off.',
    'yolov5mu.pt': 'Medium-sized YOLOv5 model providing a good balance between speed and precision.',
    'yolov5lu.pt': 'Large variant of YOLOv5 suited for tasks that prioritize accuracy over speed.',
    'yolov5xu.pt': 'Extra-large version of YOLOv5 designed for maximum accuracy in high-performance contexts.',
    'yolov5n6u.pt': 'Nano version optimized for higher input resolution (6 series) with improved real-time performance.',
    'yolov5s6u.pt': 'Small model enhanced for larger input resolutions, offering better accuracy with moderate speed.',
    'yolov5m6u.pt': 'Medium version applied to higher-resolution inputs, balancing speed and accuracy.',
    'yolov5l6u.pt': 'Large model trained for high resolution, provides improved detection capabilities with a speed compromise.',
    'yolov5x6u.pt': 'Extra-large model optimized for high-resolution input, delivering maximum accuracy.',
    'yolov6n.pt': 'Nano variant intended for tasks requiring low computational resources, such as autonomous robotics.',
    'yolov6s.pt': 'Small variant tailored for edge AI and real-time applications such as drones or delivery robots.',
    'yolov6m.pt': 'Mid-tier model designed for applications with moderate computational power consumption and high efficiency.',
    'yolov6l.pt': 'Large model offering excellent detection performance at the cost of slower inference times.',
    'yolov6l6.pt': 'High-resolution version of the YOLOv6-L for tasks that require processing in greater detail.',
    'yolov8n.pt': 'Highly optimized nano version of YOLOv8 for real-time object detection tasks.',
    'yolov8s.pt': 'Small variant of YOLOv8, trading some speed for improved accuracy while maintaining efficiency.',
    'yolov8m.pt': 'Medium YOLOv8 model catering to general-purpose detection tasks with balanced speed and performance.',
    'yolov8l.pt': 'Larger YOLOv8 variant focused on high precision for detection tasks across more complex datasets.',
    'yolov8x.pt': 'Extra-large YOLOv8 model designed for scenarios that demand maximum accuracy and detail.',
    'yolov9t.pt': 'Tiny variant of YOLOv9 with programmable gradient information, optimizing accuracy in smaller models.',
    'yolov9s.pt': 'Small variant of YOLOv9 leveraging programmable gradient information for efficient detection.',
    'yolov9m.pt': 'Medium YOLOv9 model utilizing programmable gradient information for superior results.',
    'yolov9c.pt': 'Compact YOLOv9 variant incorporating programmable gradient information for balanced tasks.',
    'yolov9e.pt': 'Experimental YOLOv9 with programmable gradient features for cutting-edge detection capabilities.',
    'yolov10n.pt': 'Nano-sized YOLOv10 model featuring NMS-free (non-maximum-suppression-free) training for faster inference.',
    'yolov10s.pt': 'Small YOLOv10 variant with NMS-free training for real-time applications.',
    'yolov10m.pt': 'Medium YOLOv10 model focused on higher accuracy and efficiency with NMS-free training methodology.',
    'yolov10l.pt': 'Large variant of YOLOv10 offering high accuracy with NMS-free training for advanced detection.',
    'yolov10x.pt': 'Extra-large YOLOv10 model designed for maximum accuracy, featuring NMS-free training at higher computational cost.',
    'yolo11n.pt': 'Nano variant delivering state-of-the-art (SOTA) performance optimized for speed and resource constraints.',
    'yolo11s.pt': 'Small model achieving SOTA object detection performance without sacrificing speed.',
    'yolo11m.pt': 'Medium model offering SOTA performance for balanced accuracy and inference speed.',
    'yolo11l.pt': 'Large model delivering SOTA performance with a focus on accuracy, suitable for intricate tasks.',
    'yolo11x.pt': 'Extra-large variant pushing SOTA performance boundaries for the most demanding object detection tasks.',
}


def get_available_models():
    """
    Recursively scans the provided directory for .tflite, .onnx and .pt model files.
    Returns a list of all found models with their full file paths.

    Returns:
        List[str]: List of paths to discovered .tflite and .pt model files.
    """
    allowed_extensions = ('.tflite', '.pt') if is_google_coral_connected() else ('.pt')
    existing_set = set()
    result = get_directory_structure(
        DATA_DIR,
        allowed_extensions,
        exclude_empty_dirs=True,
        absolute=False,
        file_processor=lambda file_path: existing_set.add(os.path.basename(file_path)),
    )

    for key, _ in yolo_descriptions.items():
        if not key in existing_set:
            item = {
                "label": key,
                "key": key,
                "data": {"name": key, "type": "Loadable model"},
            }
            result.append(item)

    return result


get_available_models()
