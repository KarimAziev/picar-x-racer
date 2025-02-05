from abc import ABCMeta, abstractmethod
from typing import Tuple

import numpy as np
from app.core.logger import Logger

logger = Logger(name=__name__)


class VideoCaptureAdapter(metaclass=ABCMeta):
    """
    Abstract class responsible for managing video capturing.
    """

    @abstractmethod
    def read(self) -> Tuple[bool, np.ndarray]:
        pass

    @abstractmethod
    def release(self) -> None:
        pass
