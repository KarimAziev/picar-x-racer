from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


def take_while(items: Sequence[T], pred: Callable[[T], bool]) -> Sequence[T]:
    result: Sequence[T] = []
    for item in items:
        if pred(item):
            result.append(item)
        else:
            break

    return result
