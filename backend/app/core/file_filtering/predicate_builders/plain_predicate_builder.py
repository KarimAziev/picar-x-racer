from __future__ import annotations

from typing import Callable

from app.core.file_filtering.predicate_builders.base_predicate_builder import (
    PredicateBuilder,
)
from app.schemas.file_filter import FileDetail, Filter, FilterField, FilterMatchMode


class PlainPredicateBuilder(PredicateBuilder):
    def supports(self, filter_field: Filter) -> bool:
        return isinstance(filter_field, FilterField)

    def build(
        self, filter_field: FilterField, field_name: str
    ) -> Callable[[FileDetail], bool]:
        mode = filter_field.match_mode
        filter_value = filter_field.value

        def filter_predicate(f: FileDetail) -> bool:
            value = getattr(f, field_name)
            if mode == FilterMatchMode.EQUALS:
                return value == filter_value
            elif mode == FilterMatchMode.CONTAINS:
                if filter_value is None:
                    return False
                return filter_value.lower() in (
                    str(value).lower() if value is not None else ""
                )
            return True

        return filter_predicate
