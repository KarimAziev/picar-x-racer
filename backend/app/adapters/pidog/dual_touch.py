import time
from typing import Literal, Union

from robot_hat.pin import Pin

DualTouchEvent = Literal["RS", "L", "LS", "R", "N"]


class DualTouch:
    """
    A dual touch sensor class used to detect left or right touches, as well as sliding
    when touches alternate within a short time frame.
    """

    SLIDE_MAX_INTERVAL: float = (
        0.5  # second, Maximum effective interval for sliding detection
    )

    def __init__(
        self, sw1: Union[int, str] = "D2", sw2: Union[int, str] = "D3"
    ) -> None:
        """
        Initialize the dual touch sensor with two pins.

        Args:
            sw1: Pin number or identifier for the left sensor. Default is "D2".
            sw2: Pin number or identifier for the right sensor. Default is "D3".
        """
        self.touch_L = Pin(sw1, mode=Pin.IN, pull=Pin.PULL_UP)
        self.touch_R = Pin(sw2, mode=Pin.IN, pull=Pin.PULL_UP)
        self.last_touch = "N"
        self.last_touch_time = 0.0

    def read(self) -> DualTouchEvent:
        """
        Determine the type of touch event based on the current state of each sensor.

        The sensors return a '1' when touched. If a touch is detected:
          - For the left sensor:
              * Returns "L" if no recent right touch is recorded.
              * Returns "RS" if the last touch was from the right sensor and the interval is within SLIDE_MAX_INTERVAL.
          - For the right sensor:
              * Returns "R" if no recent left touch is recorded.
              * Returns "LS" if the last touch was from the left sensor and the interval is within SLIDE_MAX_INTERVAL.
          - Returns "N" if no sensor is touched.

        Returns:
            A string representing the touch event.
        """
        current_time: float = time.time()

        if self.touch_L.value() == 1:
            if self.last_touch == "R" and (
                current_time - self.last_touch_time <= self.SLIDE_MAX_INTERVAL
            ):
                result: Literal["RS", "L", "LS", "R", "N"] = "RS"
            else:
                result = "L"
            self.last_touch_time = current_time
            self.last_touch = "L"
            return result

        elif self.touch_R.value() == 1:
            if self.last_touch == "L" and (
                current_time - self.last_touch_time <= self.SLIDE_MAX_INTERVAL
            ):
                result = "LS"
            else:
                result = "R"
            self.last_touch_time = current_time
            self.last_touch = "R"
            return result

        return "N"
