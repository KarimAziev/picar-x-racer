from abc import ABCMeta, abstractmethod
from typing import Tuple

import numpy as np
from app.core.logger import Logger
from app.core.video_device_abc import VideoDeviceABC
from app.schemas.camera import CameraSettings

logger = Logger(name=__name__)


class VideoCaptureAdapter(metaclass=ABCMeta):
    """
    Abstract class responsible for managing video capturing.
    """

    def __init__(self, manager: VideoDeviceABC):
        self.manager = manager

    @property
    @abstractmethod
    def settings(self) -> CameraSettings:
        """Camera settings property that must be implemented in subclasses."""
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, np.ndarray]:
        pass

    @abstractmethod
    def release(self) -> None:
        pass
