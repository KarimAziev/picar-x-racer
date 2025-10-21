"""
Module: add_annotations.py

Description:
-------------
This script is designed to automate the process of annotating images with bounding boxes and class labels,
using YOLO format label files. The script reads bounding box information from the specified label files,
applies the appropriate annotations on corresponding images (by drawing bounding boxes around identified objects),
and saves the newly annotated images to a specified output directory.

The script is primarily intended for use with datasets in YOLO (You Only Look Once) format, where each image has an
associated text file (label file) containing object class IDs and bounding box coordinates.

Functionality:
--------------
1. **Task & Input**:
   - The script reads images from a given directory that could be in `.jpg`, `.png`, or `.jpeg` formats.
   - It obtains bounding box and class ID information from YOLO-format label files. Each label file has the
     following format for each object:
       - Class ID
       - Normalized x, y coordinates for the center of the bounding box
       - Bounding box width
       - Bounding box height
     These values are normalized with respect to the image dimensions (i.e., between 0 and 1).

2. **Annotation**:
   - Bounding boxes are drawn on the image corresponding to the provided bounding box coordinates in the label file.
   - If a list of class names is provided, their names are also superimposed near the bounding boxes
     for easier image review.

3. **Output**:
   - The annotated images are saved in the specified output directory. Users can clear the output directory before new
     images are added by providing an optional flag.

Usage:
------
`add_annotations.py` can be run from the command line using the following syntax:

```bash
python add_annotations.py -i <image_dir> -o <output_dir> -l <labels_dir> -n <class_names> -C
```

Options and Arguments:
-----------------------
- `-i, --images_dir`: (**Required**) Directory containing the images to be annotated (e.g., `.jpg`, `.png`).
- `-o, --out_dir`: (**Required**) Directory where the annotated images will be saved.
- `-l, --labels_dir`: (**Optional**) Directory containing YOLO-format label files. If not provided, the script will attempt to infer the location.
- `-n, --names`: (**Optional**) List of object class names corresponding to class IDs in label files. For instance, `-n cat dog` would be used if class 0 refers to cats and class 1 refers to dogs.
- `-C, --clear_output`: (**Optional**) When set, the output directory will be cleared before saving new annotated images.

Examples:
---------
```bash
# Example 1: Annotate images with a single class label and clear output directory before running
python add_annotations.py -i ~/data/images/train -l ~/data/labels/train -o ~/output/images/train -n cat -C

# Example 2: Annotate images without clearing the output directory or specifying class names (uses default class IDs)
python add_annotations.py -i ~/data/images/val -o ~/output/images/val

# Example 3:
python add_annotations.py \
    -i ~/Dropbox/black-cat-yolo-dataset/images/train \
    -l ~/Dropbox/black-cat-yolo-dataset/labels/train \
    -o ~/Pictures/black-cat-yolo-dataset-annotations/train \
    -n cat \
    -C
```
Note:
-----
- The label files are expected to be in YOLO format, with object coordinates normalized (0-1).
- Image and label file names should match (e.g., `image1.jpg` has an annotation in `image1.txt`).
- If a YOLO label file does not exist for an image, no annotations will be applied to that image.
"""

import argparse
import os
import shutil
import signal
import sys
from pathlib import Path
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np

from app.core.logger import Logger
from app.util.file_util import (
    file_name_parent_directory,
    get_directory_name,
    get_files_with_extension,
    resolve_absolute_path,
)
from app.util.overlay_detecton import draw_overlay

logger = Logger(__name__)


class ImageAnnotator:
    def __init__(
        self,
        images_dir: str,
        out_dir: Union[Path, str],
        labels_dir: Optional[Union[Path, str]] = None,
        labels_dict: Optional[dict[int, str]] = None,
        clear_output: bool = False,
    ) -> None:
        self.images_dir = images_dir
        self.out_dir = out_dir
        self.labels_dir = labels_dir if labels_dir else self.infer_labels_dir()
        self.labels_dict = labels_dict if labels_dict else {}
        self.clear_output = clear_output

        if self.clear_output and os.path.exists(self.out_dir):
            logger.info(f"Clearing files in output directory: {self.out_dir}")
            self.clear_output_directory()
        Path(self.out_dir).mkdir(parents=True, exist_ok=True)

    def clear_output_directory(self) -> None:
        """Clears out all files in the output directory without deleting the directory itself."""
        if os.path.exists(self.out_dir):
            for filename in os.listdir(self.out_dir):
                file_path = os.path.join(self.out_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}. Reason: {e}")

    def get_label_file(self, img_path: str) -> str:
        """Determines the label file path for a given image."""
        if self.labels_dir is not None:
            return os.path.join(self.labels_dir, Path(img_path).stem + ".txt")
        else:
            parent_dir = file_name_parent_directory(img_path)
            parent_dir_name = get_directory_name(parent_dir)
            labels_dir = file_name_parent_directory(
                file_name_parent_directory(parent_dir)
            )
            label_txt_file = os.path.join(
                labels_dir, "labels", parent_dir_name, Path(img_path).stem + ".txt"
            )
            return label_txt_file

    def infer_labels_dir(self) -> str:
        """Infers the labels directory based on the images directory structure."""
        parent_dir_name = get_directory_name(self.images_dir)
        labels_dir = os.path.join(
            file_name_parent_directory(file_name_parent_directory(self.images_dir)),
            "labels",
        )

        sub_dir = os.path.join(labels_dir, parent_dir_name)

        if os.path.exists(sub_dir):
            return sub_dir

        if os.path.exists(labels_dir):
            return labels_dir

        logger.info("Labels directory couldn't be found")
        sys.exit(1)

    @staticmethod
    def parse_yolo_label_file(
        file_path: str,
    ) -> List[Tuple[int, float, float, float, float]]:
        """
        Parses a YOLO formatted label file.

        Each line in the file contains object detection data in the format:
        class_id center_x center_y width height

        :param file_path: path to the YOLO label file.
        :return: list of tuples where each tuple is (class_id, center_x, center_y, width, height)
        """
        labels = []

        with open(file_path, "r") as f:
            for line in f:
                parts = line.strip().split()

                if len(parts) != 5:
                    continue
                class_id = int(parts[0])
                center_x = float(parts[1])
                center_y = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])

                labels.append((class_id, center_x, center_y, width, height))

        return labels

    def parse_label_and_annotate_img(self, img_path: str) -> np.ndarray:
        """Reads an image and overlays annotations based on label files."""
        frame = cv2.imread(img_path)

        if frame is None:
            raise ValueError(f"Image '{img_path}' not found!")

        original_height, original_width = frame.shape[:2]
        label_file_path = self.get_label_file(img_path)
        parsed_labels = self.parse_yolo_label_file(label_file_path)

        for class_id, center_x, center_y, width, height in parsed_labels:
            label = self.labels_dict.get(class_id)
            top_left_x = int((center_x - width / 2) * original_width)
            top_left_y = int((center_y - height / 2) * original_height)
            bottom_right_x = int((center_x + width / 2) * original_width)
            bottom_right_y = int((center_y + height / 2) * original_height)

            frame = draw_overlay(
                frame,
                x1=top_left_x,
                y1=top_left_y,
                x2=bottom_right_x,
                y2=bottom_right_y,
                label=label,
            )

        return frame

    def write_annotated_img_by_labels(self, img_path: str) -> None:
        """Writes an annotated image to the output directory."""
        frame = self.parse_label_and_annotate_img(img_path)
        out_name = os.path.join(self.out_dir, os.path.basename(img_path))
        cv2.imwrite(out_name, frame)
        logger.info(f"Image saved with annotations: {out_name}")

    def process_images(self) -> None:
        """Processes all images in the images directory."""
        image_files = get_files_with_extension(
            self.images_dir, (".jpg", ".png", ".jpeg")
        )
        logger.info(f"Found {len(image_files)} images to process.")
        for file in image_files:
            self.write_annotated_img_by_labels(file)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A script to annotate images based on YOLO format label files "
        "by overlaying bounding boxes and optional labels on the images. "
        "The annotated images are saved to a specified output directory.",
        epilog="Example usage: \n"
        "python add_annotations.py -i <image_dir> -o <output_dir> -l <labels_dir> -n <class_names> -C",
    )

    parser.add_argument(
        "-i",
        "--images_dir",
        type=str,
        required=True,
        help="Path to the directory containing the images to be annotated. This directory should contain images in "
        "formats such as `.jpg`, `.jpeg`, or `.png`.",
    )

    parser.add_argument(
        "-o",
        "--out_dir",
        type=str,
        required=True,
        help="Directory where the processed images with annotations will be saved. The output directory will be created "
        "if it does not exist.",
    )

    parser.add_argument(
        "-l",
        "--labels_dir",
        type=str,
        required=False,
        help="Optional path to the directory containing YOLO label files. Each image is expected to have a corresponding "
        "YOLO label file (e.g., `image1.txt`). The label file contains class ID and bounding box information."
        "If this is not provided, the script will try to infer the label directory from the structure of the "
        "images directory.",
    )

    parser.add_argument(
        "-n",
        "--names",
        nargs="*",
        type=str,
        required=False,
        default=[],
        help="Optional list of class names for object classes. These names correspond to the class IDs specified in "
        "the YOLO label files. For example, if class ID `0` refers to 'cat' and class ID `1` refers to 'dog', "
        "you should provide `-n cat dog`.",
    )

    parser.add_argument(
        "-C",
        "--clear_output",
        action="store_true",
        required=False,
        help="If this flag is set, the output directory will be cleared before saving the new annotated images. This "
        "is useful if you want to avoid mixing previous results with the current run.",
    )

    args = parser.parse_args()
    images_dir = args.images_dir
    out_dir = args.out_dir
    labels_dir = args.labels_dir

    labels_dict = {i: label for i, label in enumerate(args.names)}

    annotator = ImageAnnotator(
        images_dir=resolve_absolute_path(images_dir),
        out_dir=out_dir,
        labels_dir=resolve_absolute_path(labels_dir) if labels_dir else labels_dir,
        labels_dict=labels_dict,
        clear_output=args.clear_output,
    )

    logger.info(
        f"Processing {images_dir} with labels from {annotator.labels_dir}, annotations will be saved to {out_dir}"
    )

    try:
        annotator.process_images()
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        sys.exit(1)


def signal_handler(sig, frame) -> None:
    logger.info("You pressed Ctrl+C! Exiting gracefully...")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    main()
