from time import sleep
from typing import TYPE_CHECKING, Optional, Union

from app.core.px_logger import Logger

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event


_log = Logger(__name__)


def led_process(
    pin: Union[str, int],
    stop_event: "Event",
    interval: float = 0.1,
) -> None:
    from gpiozero import LED

    led: Optional[LED] = None

    try:
        led = LED(pin)
        while not stop_event.is_set():
            try:
                led.on()
                sleep(interval)
                led.off()
                sleep(interval)
            except ValueError as e:
                _log.error("Aborting LED process: %s", str(e))
                break
    except (
        ConnectionError,
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
        ConnectionResetError,
    ) as e:
        _log.warning(
            "Connection-related error occurred in LED process." "Exception handled: %s",
            type(e).__name__,
        )
    except KeyboardInterrupt:
        _log.warning("LED process received KeyboardInterrupt, exiting.")
    except Exception:
        _log.error("Unhandled exception in LED process", exc_info=True)
    finally:
        _log.info("LED process is terminating")
        if led:
            _log.info("Closing LED.")
            try:
                led.close()
            except Exception as e:
                _log.warning("Failed to close LED: %s", e)
