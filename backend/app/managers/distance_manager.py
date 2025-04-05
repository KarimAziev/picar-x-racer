import os
from time import sleep
from typing import TYPE_CHECKING

from app.core.px_logger import Logger
from robot_hat import Pin

if os.getenv("ROBOT_HAT_MOCK_SMBUS"):
    from robot_hat import UltrasonicMock as Ultrasonic
else:
    from robot_hat import Ultrasonic


if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized
    from multiprocessing.synchronize import Event


logger = Logger(__name__)


def distance_process(
    trig_pin: str,
    echo_pin: str,
    stop_event: "Event",
    value: "Synchronized",
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
                logger.debug(
                    "val %s, synchronized value=%s, interval %s",
                    val,
                    value.value,
                    interval,
                )

                sleep(interval)
            except ValueError as e:
                logger.error("Aborting distance process: %s", str(e))
                break
    except (
        ConnectionError,
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
        ConnectionResetError,
    ) as e:
        logger.warning(
            "Connection-related error occurred in distance process."
            "Exception handled: %s",
            type(e).__name__,
        )
    except KeyboardInterrupt:
        logger.warning("Distance process received KeyboardInterrupt, exiting.")
    except Exception:
        logger.error("Unhandled exception in distance process", exc_info=True)
    finally:
        logger.info("Distance process is terminating.")
