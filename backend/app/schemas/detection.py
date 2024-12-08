from typing import List, Optional

from pydantic import BaseModel, Field


class DetectionSettings(BaseModel):
    """
    A schema for defining detection configuration settings.

    Attributes:
    - `model`: The name of the object detection model to be used.
    - `confidence`: The confidence threshold for detections.
    - `active`: Flag indicating whether the detection is currently active.
    - `img_size`: The image size for the detection process.
    - `labels`: A list of labels to filter for specific object detections, if desired.
    - `overlay_draw_threshold`: The maximum allowable time difference (in seconds) between
          the frame timestamp and the detection timestamp for overlay drawing to occur.
    """

    model: Optional[str] = Field(
        None,
        description="The name of the object detection model to be used. For examples: 'yolov8n.pt'.",
        examples=["yolov8n.pt", "yolo11n.pt", "yolo11m.pt"],
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="The confidence threshold for detections, between 0.0 and 1.0.",
        examples=[0.4],
    )
    active: Optional[bool] = Field(
        None,
        description="Flag indicating whether the detection is currently active.",
    )
    img_size: int = Field(
        640,
        ge=1,
        description="The image resolution size for the detection process. Default is 640.",
        examples=[320],
    )
    labels: Optional[List[str]] = Field(
        None,
        description="A list of labels to filter for specific object detections, if desired.",
        examples=[["person", "cat"]],
    )
    overlay_draw_threshold: float = Field(
        1.0,
        gt=0,
        description=(
            "The maximum allowable time difference (in seconds) between the frame timestamp "
            "and the detection timestamp for overlay drawing to occur. Must be greater than 0."
        ),
        examples=[1.0],
    )


class FileData(BaseModel):
    """
    Model representing data for an individual file or folder.

    Attributes:
    --------------
    - `name`: Name of the file or folder.
    - `type`: Type of the item (e.g., "File", "Folder", "Loadable model").
    """

    name: str = Field(
        ...,
        description="The name of the file or folder.",
        examples=["cat_320_float32.tflite", "cat_320_saved_model"],
    )
    type: str = Field(
        ...,
        description="The type of the item (e.g., 'File', 'Folder', 'Loadable model').",
        examples=["File", "Folder", "Loadable model"],
    )


class ModelChild(BaseModel):
    """
    Model representing a child item in a folder structure.

    Attributes:
    --------------
    - `key`: Unique key for the child item.
    - `label`: Display label for the child item.
    - `data`: Metadata about the child item.
    """

    key: str = Field(
        ...,
        description="Unique key for the child item.",
        examples=["cat_320_saved_model/cat_320_float32.tflite"],
    )
    label: str = Field(
        ...,
        description="Display label for the child item.",
        examples=["cat_320_float32.tflite"],
    )
    data: FileData


class ModelResponse(BaseModel):
    """
    Model representing an available object detection model or its folder.

    Attributes:
    --------------
    - `key`: Unique key for the folder or model.
    - `label`: Label for the folder or model.
    - `selectable`: Whether the model or folder is selectable (applies to folders).
    - `children`: List of child items (e.g., files in a folder). Optional for non-folder items.
    - `data`: Metadata about the model or folder.
    """

    key: str = Field(
        ...,
        description="Unique key for the folder or model.",
        examples=["cat_320_saved_model", "yolo11s.pt"],
    )
    label: str = Field(
        ...,
        description="Display label for the folder or model.",
        examples=["cat_320_saved_model", "yolo11s.pt"],
    )
    selectable: Optional[bool] = Field(
        None,
        description="Whether the folder/model is selectable (applies mainly to folders).",
        examples=[False],
    )
    children: Optional[List[ModelChild]] = Field(
        None,
        description="List of child items in the folder (applies to folder items).",
        examples=[
            [
                {
                    "key": "cat_320_saved_model/cat_320_float32.tflite",
                    "label": "cat_320_float32.tflite",
                    "data": {
                        "name": "cat_320_float32.tflite",
                        "type": "File",
                    },
                }
            ]
        ],
    )
    data: FileData
