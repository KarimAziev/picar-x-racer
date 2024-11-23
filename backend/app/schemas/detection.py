from typing import List, Optional

from pydantic import BaseModel


class DetectionSettings(BaseModel):
    model: Optional[str] = None
    confidence: Optional[float] = None
    active: Optional[bool] = None
    img_size: int = 640
    labels: Optional[List[str]] = None
