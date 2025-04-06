from abc import ABC, abstractmethod
from typing import Callable

from app.schemas.file_filter import FileDetail, Filter


class PredicateBuilder(ABC):
    @abstractmethod
    def supports(self, filter_field: Filter) -> bool:
        """Return True if this builder can handle the type of filter_field."""
        pass

    @abstractmethod
    def build(self, filter_field, field_name: str) -> Callable[[FileDetail], bool]:
        """Return the predicate function given the filter_field and field name."""
        pass
