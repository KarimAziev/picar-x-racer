import os
from time import sleep
from typing import TYPE_CHECKING, Union

from app.core.px_logger import Logger
from robot_hat import Pin

if os.getenv("ROBOT_HAT_MOCK_SMBUS"):
    from robot_hat import UltrasonicMock as Ultrasonic
else:
    from robot_hat import Ultrasonic


if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized
    from multiprocessing.synchronize import Event


_log = Logger(__name__)


def distance_process(
    trig_pin: Union[int, str],
    echo_pin: Union[int, str],
    stop_event: "Event",
    value: "Synchronized[float]",
    interval: float = 0.01,
    timeout=0.017,
):
    try:
        ultrasonic = Ultrasonic(
            Pin(trig_pin),
            Pin(echo_pin, mode=Pin.IN, pull=Pin.PULL_DOWN),
            timeout=timeout,
        )
        while not stop_event.is_set():
            try:
                val = float(ultrasonic.read())
                value.value = val
                _log.debug(
                    "val %s, synchronized value=%s, interval %s",
                    val,
                    value.value,
                    interval,
                )

                sleep(interval)
            except ValueError as e:
                _log.error("Aborting distance process: %s", str(e))
                break
    except (
        ConnectionError,
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
        ConnectionResetError,
    ) as e:
        _log.warning(
            "Connection-related error occurred in distance process."
            "Exception handled: %s",
            type(e).__name__,
        )
    except KeyboardInterrupt:
        _log.warning("Distance process received KeyboardInterrupt, exiting.")
    except Exception:
        _log.error("Unhandled exception in distance process", exc_info=True)
    finally:
        _log.info("Distance process is terminating.")
