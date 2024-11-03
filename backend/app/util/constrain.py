from typing import Union


def constrain(
    x: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]
):
    """
    Constrains value to be within a range.
    """
    return max(min_val, min(max_val, x))
