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
        self,
        current_distance: float,
        interval: float,
        relative_speed: int,
        direction: int,
    ) -> Optional[float]:
        """
        Process a distance measurement and estimate speed in km/h using an externally provided
        interval, relative speed (0-100%), and direction (1, -1, or 0).

        Args:
            current_distance: Current distance reading from the ultrasonic sensor (in centimeters).
                              A value of -1 indicates a failed reading.
            interval: The time interval between successive measurements (in seconds).
            relative_speed: Commanded relative speed (0-100% of capabilities)
            direction: Movement direction: 1 for forward, -1 for backward, 0 for stop.

        Returns:
            Estimated speed in km/h, or None if not enough data or if the reading failed.
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

            max_speed_kmph = 100.0
            expected_speed = (relative_speed / 100.0) * max_speed_kmph

            if abs(estimated_speed - expected_speed) > (0.3 * expected_speed):
                logger.debug(
                    "Measured speed (%skm/h) deviates significantly from commanded speed (%skm/h).",
                    estimated_speed,
                    expected_speed,
                )

        self.previous_distance = current_distance
        result = (
            math.trunc(estimated_speed * 10) / 10
            if estimated_speed is not None
            else None
        )
        logger.debug("speed=%skm/h", result)
        return estimated_speed
