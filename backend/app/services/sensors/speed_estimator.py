import math
from typing import Optional

from app.core.px_logger import Logger
from app.core.singleton_meta import SingletonMeta

logger = Logger(__name__)


class SpeedEstimator(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.previous_filtered_distance: Optional[float] = None

        self.x: Optional[float] = None
        self.P: Optional[float] = None

        self.Q = 0.1
        self.R = 1.0

    def kalman_update(self, measurement: float) -> float:
        """
        Perform a simple 1D Kalman filter update with the new measurement.
        Returns the filtered value.
        """
        if self.x is None:
            self.x = measurement
            self.P = 1.0
        else:
            assert self.P is not None, "self.P should not be None here."
            P_pred = self.P + self.Q

            K = P_pred / (P_pred + self.R)
            self.x = self.x + K * (measurement - self.x)
            self.P = (1 - K) * P_pred

        return self.x

    def process_distance(
        self,
        current_distance: float,
        interval: float,
        relative_speed: int,
    ) -> Optional[float]:
        """
        Process a distance measurement and estimate speed in km/h by
        using a simple Kalman filter to smooth the raw sensor reading.
        The calculation is based on the difference between consecutive
        filtered distance values.

        Args:
            current_distance: Current distance reading from the sensor (in centimeters).
                              A value of -1 indicates a failed reading.
            interval: The time interval between successive measurements (in seconds).
            relative_speed: Commanded relative speed (0-100% of capabilities).

        Returns:
            Estimated speed in km/h (truncated to one decimal) or None if the reading failed.
        """
        if current_distance == -1:
            logger.warning(
                "Failed distance reading (value=-1). Skipping speed estimation."
            )
            return None

        filtered_distance = self.kalman_update(current_distance)

        estimated_speed: Optional[float] = None
        if self.previous_filtered_distance is not None and interval > 0:
            speed_cm_s = (
                abs(filtered_distance - self.previous_filtered_distance) / interval
            )
            estimated_speed = speed_cm_s * 0.036

            max_speed_kmph = 100.0
            expected_speed = (relative_speed / 100.0) * max_speed_kmph

            if abs(estimated_speed - expected_speed) > (0.3 * expected_speed):
                logger.debug(
                    "Measured speed (%skm/h) deviates significantly from commanded speed (%skm/h).",
                    estimated_speed,
                    expected_speed,
                )

        self.previous_filtered_distance = filtered_distance

        truncated_speed = (
            (math.trunc(estimated_speed * 10) / 10)
            if estimated_speed is not None
            else None
        )

        logger.debug(
            "speed=%skm/h, previous filtered=%.2f -> current filtered=%.2f",
            truncated_speed,
            (
                self.previous_filtered_distance
                if self.previous_filtered_distance is not None
                else 0
            ),
            filtered_distance,
        )

        return truncated_speed
