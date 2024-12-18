from queue import Empty, Full, Queue
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    import multiprocessing as mp

from app.util.logger import Logger

logger = Logger(__name__)


def clear_queue(qitem: Optional[Union[Queue, "mp.Queue"]]):
    if qitem is None:
        return None
    messages = []
    try:
        while qitem and not qitem.empty():
            try:
                msg = qitem.get_nowait()
                messages.append(msg)
            except Empty:
                pass
            except BrokenPipeError as e:
                logger.error("Get from qitem failed: %s", e)
                return None
    except BrokenPipeError as e:
        logger.error("Clear queue failed due to BrokenPipeError: %s", e)
    return messages


def get_last_message(qitem: Optional[Union[Queue, "mp.Queue"]]):
    messages = clear_queue(qitem)

    if isinstance(messages, list) and len(messages) > 0:
        return messages.pop()


def put_to_queue(
    qitem: Optional[Union[Queue, "mp.Queue"]],
    item,
    block=False,
    timeout: Optional[int] = None,
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
    except Full:
        pass
    except BrokenPipeError as e:
        logger.error("Put to qitem failed %s", e)


def clear_and_put(
    qitem: Optional[Union[Queue, "mp.Queue"]],
    item,
    block=False,
    timeout: Optional[int] = None,
):
    if qitem is None:
        return None

    clear_queue(qitem)
    return put_to_queue(qitem, item, block=block, timeout=timeout)
