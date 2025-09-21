import logging
from typing import List


class ExcludePathFilter(logging.Filter):
    """
    A logging filter to exclude logs containing specific paths.
    """

    def __init__(self, excluded_paths: List) -> None:
        super().__init__()
        self.excluded_paths = excluded_paths

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Returns False if the log record's message contains any of the excluded paths.
        """
        return not any(path in record.getMessage() for path in self.excluded_paths)
