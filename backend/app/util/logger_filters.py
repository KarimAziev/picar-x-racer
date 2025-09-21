import time
from collections import defaultdict
from logging import Filter


class RateLimitFilter(Filter):
    def __init__(self, limit=10) -> None:
        super().__init__()
        self.limit = limit
        self.log_timestamps = defaultdict(float)

    def filter(self, record) -> bool:
        msg = record.getMessage()
        if '"type":"player",' not in msg:
            return True
        else:
            current_time = time.time()

            if current_time - self.log_timestamps[msg] > self.limit:
                self.log_timestamps[msg] = current_time
                return True
            return False


class ExcludeBinaryAndAssetsFilter(Filter):
    def filter(self, record) -> bool:
        msg = record.getMessage()
        return "> BINARY " not in msg and "GET /assets/" not in msg
