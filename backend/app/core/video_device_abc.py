from abc import ABCMeta, abstractmethod
from typing import List

from app.core.logger import Logger
from app.schemas.camera import DeviceType

logger = Logger(name=__name__)


class VideoDeviceABC(metaclass=ABCMeta):
    """
    Abstract class responsible for managing video devices.
    """

    @abstractmethod
    def list_video_devices(self) -> List[DeviceType]:
        """High-level public method to list video devices."""
        pass
