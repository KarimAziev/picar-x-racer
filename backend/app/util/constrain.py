from typing import TypeVar

T = TypeVar('T', int, float)


def constrain(x: T, min_val: T, max_val: T):
    """
    Constrains value to be within a range.
    """
    return max(min_val, min(max_val, x))
