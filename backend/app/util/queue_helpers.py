import queue
from typing import TYPE_CHECKING, Any, List, Optional, Union

if TYPE_CHECKING:
    from queue import Queue
    import multiprocessing as mp

from app.core.logger import Logger

logger = Logger(__name__)


def clear_queue(
    qitem: Optional[Union["Queue", "mp.Queue"]], reraise: bool = False
) -> Optional[List[Any]]:
    if qitem is None:
        return None
    messages: List[Any] = []
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
    item: Any,
    block: bool = False,
    timeout: Optional[float] = None,
    reraise: bool = False,
) -> Optional[Any]:

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
    return None


def clear_and_put(
    qitem: Optional[Union["Queue", "mp.Queue"]],
    item: Any,
    block: bool = False,
    timeout: Optional[float] = None,
) -> Optional[Any]:

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
    ) as e:
        logger.warning(
            "Failed to put data into the queue due to a connection-related issue: %s",
            type(e).__name__,
        )
    return None
