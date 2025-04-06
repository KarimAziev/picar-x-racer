from typing import Callable

from app.core.file_filtering.predicate_builders.base_predicate_builder import (
    PredicateBuilder,
)
from app.schemas.file_filter import FileDetail, Filter, FilterBoolField


class BoolPredicateBuilder(PredicateBuilder):
    def supports(self, filter_field: Filter) -> bool:
        return isinstance(filter_field, FilterBoolField)

    def build(
        self, filter_field: FilterBoolField, field_name: str
    ) -> Callable[[FileDetail], bool]:
        if filter_field.value is None:
            return lambda _: True

        def bool_predicate(f: FileDetail) -> bool:
            value = getattr(f, field_name)
            return value == filter_field.value

        return bool_predicate
