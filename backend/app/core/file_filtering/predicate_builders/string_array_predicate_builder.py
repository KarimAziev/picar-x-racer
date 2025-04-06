from __future__ import annotations

from typing import Callable

from app.core.file_filtering.predicate_builders.base_predicate_builder import (
    PredicateBuilder,
)
from app.core.logger import Logger
from app.schemas.file_filter import (
    FileDetail,
    Filter,
    FilterFieldStringArray,
    FilterMatchMode,
)

_log = Logger(name=__name__)


class StringArrayPredicateBuilder(PredicateBuilder):
    def supports(self, filter_field: Filter) -> bool:
        return isinstance(filter_field, FilterFieldStringArray)

    def build(
        self, filter_field: FilterFieldStringArray, field_name: str
    ) -> Callable[[FileDetail], bool]:
        _log.debug(
            "Building string array predicate for %s with match mode %s",
            field_name,
            filter_field.match_mode,
        )
        if not filter_field.value:
            return lambda _: True

        filter_vals = {val.lower() for val in filter_field.value}
        mode = filter_field.match_mode

        def string_predicate(f: FileDetail) -> bool:
            attr_val = (getattr(f, field_name, "") or "").lower()
            if mode == FilterMatchMode.IN:
                return attr_val in filter_vals
            elif mode == FilterMatchMode.EQUALS:
                return attr_val == list(filter_vals)[0]
            elif mode == FilterMatchMode.CONTAINS:
                return any(val in attr_val for val in filter_vals)
            return True

        return string_predicate
