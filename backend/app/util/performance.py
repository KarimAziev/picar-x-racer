import functools
import time
from typing import Any, Callable, Optional, Type, TypeVar

from app.core.logger import Logger

_logger = Logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class Timer:
    """

    Usage:
    ```python
    with Timer("perform_detection"):
        detection_result = perform_detection(
            frame=frame,
            yolo_model=yolo_model,
            confidence_threshold=confidence_threshold,
            verbose=verbose,
            original_height=frame_data["original_height"],
            original_width=frame_data["original_width"],
            resized_height=frame_data["resized_height"],
            resized_width=frame_data["resized_width"],
            pad_left=frame_data["pad_left"],
            pad_top=frame_data["pad_top"],
            should_resize=frame_data["should_resize"],
            labels_to_detect=labels,
        )
    ```
    """

    def __init__(self, label: str = "") -> None:
        self.label: str = label
        self.start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.elapsed = time.perf_counter() - self.start
        _logger.info(f"{self.label} took {self.elapsed:.4f} seconds")


def measure_time(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start: float = time.perf_counter()
        result: Any = func(*args, **kwargs)
        elapsed: float = time.perf_counter() - start
        _logger.info(f"{func.__name__} took {elapsed:.4f} seconds")
        return result

    return wrapper  # type: ignore
