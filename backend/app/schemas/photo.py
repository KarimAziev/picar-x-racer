from typing import Literal, Optional

from app.config.video_enhancers import frame_enhancers
from app.schemas.camera import CameraSettings
from app.schemas.stream import ImageRotation
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class PhotoCameraSettings(CameraSettings):
    """An explicit camera mode for a still photograph."""

    device: Optional[str] = Field(..., min_length=1)
    width: Optional[int] = Field(..., gt=0, le=16384)
    height: Optional[int] = Field(..., gt=0, le=16384)
    fps: Optional[float] = Field(default=None, gt=0, le=240)

    @model_validator(mode="after")
    def require_camera_mode(self) -> Self:
        if self.device is None or self.width is None or self.height is None:
            raise ValueError("Photo presets require a device, width, and height")
        return self


class PhotoPreset(BaseModel):
    """Camera acquisition and image output settings for a photograph."""

    id: str = Field(min_length=1, max_length=100, pattern=r"^[\w-]+$")
    name: str = Field(min_length=1, max_length=100)
    camera: PhotoCameraSettings
    format: Literal[".jpg", ".png"] = ".jpg"
    quality: int = Field(default=95, ge=0, le=100)
    rotation: ImageRotation = ImageRotation.rotate_0
    enhance_mode: Optional[str] = None
    settle_seconds: float = Field(default=0.5, ge=0, le=5)

    @model_validator(mode="after")
    def validate_enhancer(self) -> Self:
        if self.enhance_mode is not None and self.enhance_mode not in frame_enhancers:
            raise ValueError("Unknown photo effect")
        return self


class PhotoSettings(BaseModel):
    presets: list[PhotoPreset] = Field(default_factory=list, max_length=100)
    selected_preset_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_presets(self) -> Self:
        ids = [preset.id for preset in self.presets]
        if len(ids) != len(set(ids)):
            raise ValueError("Photo preset IDs must be unique")
        if self.selected_preset_id is not None and self.selected_preset_id not in ids:
            raise ValueError("Selected photo preset does not exist")
        return self


class PhotoCaptureRequest(BaseModel):
    preset_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
