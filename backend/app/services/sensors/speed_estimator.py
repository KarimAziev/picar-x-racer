import math
from typing import Optional

from app.core.px_logger import Logger
from app.core.singleton_meta import SingletonMeta

logger = Logger(__name__)


class SpeedEstimator(metaclass=SingletonMeta):
    def __init__(
        self,
    ) -> None:
        self.previous_time: Optional[float] = None
        self.previous_distance: Optional[float] = None

    def process_distance(
        self, current_distance: float, interval: float
    ) -> Optional[float]:
        """
        Process a distance measurement and estimate speed in km/h.

        Args:
            current_distance: Current distance reading from the ultrasonic sensor (in centimeters).
            interval: The time interval between successive measurements (in seconds).

        Returns:
            Estimated speed in km/h, or None if not enough data.
        """
        if current_distance == -1:
            logger.warning(
                "Failed distance reading (value=-1). Skipping speed estimation."
            )
            return None
        estimated_speed: Optional[float] = None

        if self.previous_distance is not None and interval > 0:
            speed_cm_s = abs(current_distance - self.previous_distance) / interval

            estimated_speed = speed_cm_s * 0.036

        truncated_speed = (
            math.trunc(estimated_speed * 10) / 10
            if estimated_speed is not None
            else None
        )
        logger.debug(
            "speed=%skm/h, %.2f -> %.2f",
            truncated_speed,
            self.previous_distance,
            current_distance,
        )
        self.previous_distance = current_distance
        return truncated_speed
