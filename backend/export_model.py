"""
Export YOLO Model to Coral Edge TPU Format.

This script exports a YOLO model (e.g., `yolov8n.pt`) to a format compatible with the
Google Coral Edge TPU. It uses the `ultralytics` library to handle the model export process.

## Why Use 320x320 img Size?

A user on the Google Coral Edge TPU GitHub issue tracker recommended using an image size
of 192x192 to prevent inference crashes. However, this recommendation did not come from the
official Google Coral development team, and many issues, including this one, have gone
unaddressed in the repository.

Although 192x192 is a suggested workaround from a community member, **we opt to export the model
using 320x320** because it provides a better balance between **prediction accuracy**
and **model size**.

- A higher image resolution (320x320) improves object detection accuracy, albeit with
  a slight increase in processing time.
- The Edge TPU can efficiently handle this resolution with minimal performance impact.

For more details on the unaddressed repository issues, see:
[GitHub Issue #773](https://github.com/google-coral/edgetpu/issues/773).

The original issue referenced:
**[Yolov8n inference crashes with "Deadline exceeded: USB transfer error 2 [LibUsbDataOutCallback]"]**

## Recommended Export Environment

To use the Edge TPU, you must convert your model into a compatible format. The export process is recommended to be run
on a machine like **Google Colab**, **x86_64 Linux**, or in the official **Ultralytics Docker container**,
as the Edge TPU compiler is unavailable on ARM-based platforms like the **Raspberry Pi**.

Check the official Ultralytics documentation for further details:
[Ultralytics Documentation](https://docs.ultralytics.com/guides/coral-edge-tpu-on-raspberry-pi/#can-i-export-my-ultralytics-yolov8-model-to-be-compatible-with-coral-edge-tpu)

## Command-Line Arguments:

- `-m` / `--model`: Path to the YOLO model file to export (e.g., `yolov8n.pt`). Defaults to a path specified in the config file.
- `-o` / `--out-model`: Output path for saving the exported model file in the Edge TPU format (`.tflite`).
- `-s` / `--imgsz`: Image size for the export process—320x320 is the default, which balances accuracy and Edge TPU performance.

This script streamlines YOLO model export to Edge TPU format, ensuring the model is ready for use on Google Coral devices.

### Examples
----------

1. **Export using relative paths** (paths will expand to the project data directory, e.g.):

   ```bash
   python export_model.py -m "my_model.pt" -o "your_output_file_edgetpu.tflite" -s 256
   -> "/path-to-project/data/my_model.pt" and "/path-to-project/your_output_file_edgetpu.tflite"
   ```

2. **Export using absolute paths**:

   ```bash
   python export_model.py -m "/path/to/your_model.pt" -o "/path/to/your_output_file_edgetpu.tflite" -s 256
   ```

3. **Export using defaults specified in the `.env` file** (refer to `.env.example` for guidance):

   ```bash
   python export_model.py
   ```

"""

import argparse
import os
from typing import Optional

from dotenv import load_dotenv

from app.util.file_util import (
    file_to_relative,
    is_parent_directory,
    resolve_absolute_path,
)


def export_yolo_model_to_edgetpu(
    yolo_model_path: str, target_path: Optional[str], imgsz: int
):
    from ultralytics import YOLO

    from app.config.config import settings

    yolo_model_path = resolve_absolute_path(yolo_model_path, settings.DATA_DIR)
    if target_path is None:
        target_path = f"{os.path.splitext(yolo_model_path)[0]}_{imgsz}_edgetpu.tflite"
    target_path = resolve_absolute_path(target_path, settings.DATA_DIR)

    print(f"Loading model {yolo_model_path}, will be exported to {target_path}")
    model = YOLO(yolo_model_path)

    print(f"Starting exporting model to {target_path}")

    export_file = model.export(
        format="edgetpu" if target_path.endswith(".tflite") else "ncnn", imgsz=imgsz
    )

    if os.path.exists(export_file):
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)

        os.replace(export_file, target_path)

        print(f"\nModel exported and copied")
        print(
            f"To use it add the following line to the {os.path.join(os.path.dirname(os.path.realpath(__file__)), '.env')}:\n"
        )
        print(
            f"YOLO_MODEL_EDGE_TPU_PATH={target_path if not is_parent_directory(settings.DATA_DIR, target_path) else file_to_relative(target_path, settings.DATA_DIR)}"
        )
    else:
        raise FileNotFoundError(f"Exported file not found: {export_file}")


def parse_arguments():
    from app.config.config import settings

    parser = argparse.ArgumentParser(
        description="Export YOLO model to Edge TPU format.",
        epilog=(
            "Example usage:\n"
            "--------------\n"
            "1. Export using relative paths:\n"
            '   python export_model.py -m "my_model.pt" -o "your_output_file_edgetpu.tflite" -s 256\n'
            "   -> Output: /path-to-project/data/my_model.pt & /path-to-project/your_output_file_edgetpu.tflite\n\n"
            "2. Export using absolute paths:\n"
            '   python export_model.py -m "/path/to/your_model.pt" -o "/path/to/your_output_file_edgetpu.tflite" -s 256\n\n'
            "3. Export using defaults from the .env file:\n"
            "   python export_model.py\n\n"
            "Key Notes:\n"
            "- `-s` or `--imgsz`: Image size (default: 256).\n"
            "- `-m` or `--model`: Path to the YOLO model (default: as per .env or config file).\n"
            "- `-o` or `--out-model`: Output path for the exported .tflite file (defaults based on config).\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    default_edge_tpu = os.getenv(
        "YOLO_MODEL_EDGE_TPU_PATH",
    )

    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default=settings.YOLO_MODEL_PATH,
        help=(
            "Path to the YOLO model file to export.\n"
            f"(Default: {settings.YOLO_MODEL_PATH})"
        ),
    )
    parser.add_argument(
        "-o",
        "--out-model",
        type=str,
        default=default_edge_tpu,
        help=(
            (
                "Output path to save the exported model file.\n"
                f"(Default: {default_edge_tpu})"
            )
            if default_edge_tpu
            else "Output path to save the exported model file"
        ),
    )
    parser.add_argument(
        "-s",
        "--imgsz",
        type=int,
        default=256,
        help="Image size for the model export. (Default: 256)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    env_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".env")

    if os.path.exists(env_file):
        print(f"Loading ENV file {env_file}")
        load_dotenv(env_file)
    args = parse_arguments()

    export_yolo_model_to_edgetpu(
        yolo_model_path=args.model,
        target_path=args.out_model,
        imgsz=args.imgsz,
    )
