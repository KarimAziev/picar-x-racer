def constrain(x: int, min_val: int, max_val: int):
    """
    Constrains value to be within a range.
    """
    return max(min_val, min(max_val, x))
