import random
import os
from time import sleep
from typing import TYPE_CHECKING

from app.util.logger import Logger
from robot_hat import Pin, Ultrasonic

if TYPE_CHECKING:
    from multiprocessing.sharedctypes import Synchronized
    from multiprocessing.synchronize import Event


logger = Logger(__name__)

use_mock = os.getenv("ROBOT_HAT_MOCK_SMBUS")


def distance_process(
    echo_pin: str,
    trig_pin: str,
    stop_event: "Event",
    value: "Synchronized",
    interval: float = 0.01,
    timeout=0.017,
):
    echo = Pin(echo_pin)
    trig = Pin(trig_pin)
    ultrasonic = Ultrasonic(trig, echo, timeout=timeout)
    try:
        while not stop_event.is_set():
            try:
                val = round(
                    float(random.uniform(20, 300) if use_mock else ultrasonic.read()), 2
                )
                value.value = val
                logger.info("%s val, interval %s", val, interval)
                sleep(interval)
            except ValueError as e:
                logger.error("Aborting distance process: %s", str(e))
                break
            except Exception as e:
                logger.error("Unhandled exception")
                break
    except BrokenPipeError:
        logger.warning("Distance process received BrokenPipeError, exiting.")
    except KeyboardInterrupt:
        logger.warning("Distance process received KeyboardInterrupt, exiting.")
    finally:
        logger.info("Distance process is terminating.")
