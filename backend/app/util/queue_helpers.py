import queue
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from queue import Queue
    import multiprocessing as mp

from app.util.logger import Logger

logger = Logger(__name__)


def clear_queue(qitem: Optional[Union["Queue", "mp.Queue"]], reraise=False):
    if qitem is None:
        return None
    messages = []
    try:
        while qitem and not qitem.empty():
            try:
                msg = qitem.get_nowait()
                messages.append(msg)
            except queue.Empty:
                pass
    except (
        ConnectionError,
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
        ConnectionResetError,
    ) as e:
        logger.warning(
            "Connection-related error occurred while clearing queue. "
            "Exception handled: %s",
            type(e).__name__,
        )
        if reraise:
            raise
    return messages


def put_to_queue(
    qitem: Optional[Union["Queue", "mp.Queue"]],
    item,
    block=False,
    timeout: Optional[int] = None,
    reraise=False,
):

    if qitem is None:
        return None
    try:
        if block is False:
            qitem.put(item, block=False)
            return item
        else:
            qitem.put(item, block=block, timeout=timeout)
            return item
    except queue.Full:
        pass
    except (
        ConnectionError,
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
        ConnectionResetError,
    ):
        if reraise:
            raise


def clear_and_put(
    qitem: Optional[Union["Queue", "mp.Queue"]],
    item,
    block=False,
    timeout: Optional[int] = None,
):

    if qitem is None:
        return None

    try:
        while qitem and not qitem.empty():
            try:
                qitem.get_nowait()
            except queue.Empty:
                pass
    except (
        ConnectionError,
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
        ConnectionResetError,
    ) as e:
        logger.warning(
            "Failed to clear the queue to connection error: %s",
            type(e).__name__,
        )
        return

    try:
        if block is False:
            qitem.put(item, block=False)
            return item
        else:
            qitem.put(item, block=block, timeout=timeout)
            return item
    except queue.Full:
        pass
    except (
        ConnectionError,
        ConnectionRefusedError,
        BrokenPipeError,
        EOFError,
        ConnectionResetError,
    ) as e:
        logger.warning(
            "Failed to put the %s to queue due to connection related issue: %s",
            item,
            type(e).__name__,
        )
