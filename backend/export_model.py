"""
To use the Edge TPU, you need to convert your model into a compatible format. It
is recommended that you run export on Google Colab, x86_64 Linux machine, using
the official Ultralytics Docker container, or using Ultralytics HUB, since the
Edge TPU compiler is not available on ARM.

See https://docs.ultralytics.com/guides/coral-edge-tpu-on-raspberry-pi/#can-i-export-my-ultralytics-yolov8-model-to-be-compatible-with-coral-edge-tpu

Note, the documentation doesn't mention it,
but the image size of exporting model should be 192*192, othervise you got an error "USB transfer error 2".
See https://github.com/google-coral/edgetpu/issues/773#issuecomment-1985745050
"""

import os

from ultralytics import YOLO

from app.config.paths import YOLO_MODEL_EDGE_TPU_PATH, YOLO_MODEL_PATH


def export_yolo_model_to_edgetpu(yolo_model_path, target_path, imgsz=(192, 192)):
    model = YOLO(yolo_model_path)

    # Export the model to Edge TPU format.
    export_file = model.export(format="edgetpu", imgsz=imgsz)

    if os.path.exists(export_file):
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)

        os.replace(export_file, target_path)
        print(f"Model exported and copied to {target_path}")
    else:
        raise FileNotFoundError(f"Exported file not found: {export_file}")


if __name__ == "__main__":
    export_yolo_model_to_edgetpu(
        YOLO_MODEL_PATH, YOLO_MODEL_EDGE_TPU_PATH, imgsz=(192, 256)
    )
