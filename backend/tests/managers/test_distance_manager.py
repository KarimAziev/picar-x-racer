import os
import unittest
import warnings
from multiprocessing.sharedctypes import Synchronized
from multiprocessing.synchronize import Event
from typing import cast
from unittest.mock import patch


class DummyEvent:
    """
    Dummy event that will return False for a set number of calls and then True.
    This lets one loop iteration occur before the while condition becomes False.
    """

    def __init__(self, calls_before_set: int = 1):
        self._calls = 0
        self._calls_before_set = calls_before_set

    def is_set(self) -> bool:
        self._calls += 1
        return self._calls > self._calls_before_set


class DummySynchronized:
    """
    A dummy “shared value” container. In production this might be a
    multiprocessing.Value or other synchronized object.
    """

    def __init__(self, value: float = 0.0):
        self.value = value


class FakeUltrasonicValid:
    """
    Fake ultrasonic sensor that returns a valid float value.
    """

    mock_read_result = 79.492

    def __init__(self, trig_pin, echo_pin, timeout):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.timeout = timeout
        self.call_count = 0

    def read(self):
        self.call_count += 1
        return self.mock_read_result


class FakeUltrasonicInvalid:
    """
    Fake ultrasonic sensor that returns an invalid reading (a non-float)
    so that a ValueError is raised.
    """

    def __init__(self, trig_pin, echo_pin, timeout):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.timeout = timeout

    def read(self):
        # Cause a ValueError in the distance_process.
        return "invalid"


class TestDistanceProcess(unittest.TestCase):

    def setUp(self) -> None:
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        self.trig_pin = "D2"
        self.echo_pin = "D3"
        self.stop_event = DummyEvent(calls_before_set=1)
        self.shared_value = DummySynchronized(0.0)
        self.patched_env = {
            **dict(os.environ),
            "ROBOT_HAT_MOCK_SMBUS": "1",
            "GPIOZERO_PIN_FACTORY": "mock",
        }

    @patch("app.managers.distance_manager.sleep", lambda interval: None)
    @patch("app.managers.distance_manager.Ultrasonic", new=FakeUltrasonicValid)
    def test_valid_read(self):
        """
        Test that with a valid sensor reading the synchronized value updates.
        """

        with patch.dict(os.environ, self.patched_env):
            from app.core.logger import Logger
            from app.managers.distance_manager import distance_process

            with patch.object(Logger, "info") as mock_logger_info:
                distance_process(
                    trig_pin=self.trig_pin,
                    echo_pin=self.echo_pin,
                    stop_event=cast(Event, self.stop_event),
                    value=cast(Synchronized, self.shared_value),
                    interval=0.001,
                    timeout=0.017,
                )
                self.assertEqual(
                    self.shared_value.value, FakeUltrasonicValid.mock_read_result
                )
                mock_logger_info.assert_called_once()

    @patch("app.managers.distance_manager.sleep", lambda interval: None)
    @patch("app.managers.distance_manager.Ultrasonic", new=FakeUltrasonicInvalid)
    def test_invalid_read_breaks_loop(self):
        """
        Test that an invalid sensor reading (causing a ValueError) logs an error and breaks out.
        """
        from app.core.logger import Logger

        with patch.dict(os.environ, self.patched_env):
            from app.managers.distance_manager import distance_process

            with patch.object(Logger, "error") as mock_logger_error:
                distance_process(
                    trig_pin=self.trig_pin,
                    echo_pin=self.echo_pin,
                    stop_event=cast(Event, self.stop_event),
                    value=cast(Synchronized, self.shared_value),
                    interval=0.001,
                    timeout=0.017,
                )

            mock_logger_error.assert_called_once()
            self.assertEqual(self.shared_value.value, 0.0)

    @patch("app.managers.distance_manager.sleep", lambda interval: None)
    @patch("app.managers.distance_manager.Ultrasonic", new=FakeUltrasonicValid)
    def test_stop_event_prevents_loop(self):
        """
        Test that if the stop_event is already set, the sensor loop is never executed
        and the shared value remains unchanged.
        """
        from app.core.logger import Logger

        class AlwaysSetEvent:
            def is_set(self) -> bool:
                return True

        always_set_event = AlwaysSetEvent()
        with patch.dict(os.environ, self.patched_env):
            from app.managers.distance_manager import distance_process

            with patch.object(Logger, "info") as mock_logger_info:
                distance_process(
                    trig_pin=self.trig_pin,
                    echo_pin=self.echo_pin,
                    stop_event=cast(Event, always_set_event),
                    value=cast(Synchronized, self.shared_value),
                    interval=0.001,
                    timeout=0.017,
                )
                mock_logger_info.assert_called_once()
                self.assertEqual(self.shared_value.value, 0.0)


if __name__ == "__main__":
    unittest.main()
