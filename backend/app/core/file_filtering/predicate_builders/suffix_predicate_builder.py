from __future__ import annotations

from typing import Callable

from app.core.file_filtering.predicate_builders.base_predicate_builder import (
    PredicateBuilder,
)
from app.core.logger import Logger
from app.schemas.file_filter import FileDetail, Filter, FilterFieldStringArray

_log = Logger(__name__)


class SuffixPredicateBuilder(PredicateBuilder):
    def supports(self, filter_field: Filter) -> bool:
        return isinstance(filter_field, FilterFieldStringArray)

    def build(
        self, filter_field: FilterFieldStringArray, field_name: str
    ) -> Callable[[FileDetail], bool]:
        _log.debug("Building suffix predicate for %s", field_name)

        if not filter_field.value:
            return lambda _: True

        suffixes = tuple(val.lower() for val in filter_field.value)

        def suffix_predicate(f: FileDetail) -> bool:
            return f.name.lower().endswith(suffixes)

        return suffix_predicate
