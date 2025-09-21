from typing import List, Optional

from app.core.file_filtering.predicate_builders.base_predicate_builder import (
    PredicateBuilder,
)
from app.core.file_filtering.predicate_builders.bool_predicate_builder import (
    BoolPredicateBuilder,
)
from app.core.file_filtering.predicate_builders.datetime_predicate_builder import (
    DateTimePredicateBuilder,
)
from app.core.file_filtering.predicate_builders.plain_predicate_builder import (
    PlainPredicateBuilder,
)
from app.core.file_filtering.predicate_builders.string_array_predicate_builder import (
    StringArrayPredicateBuilder,
)
from app.core.logger import Logger
from app.schemas.file_filter import FilterField

logger = Logger(__name__)


class PredicateBuilderFactory:
    """
    Factory to select appropriate predicate builders based on filter field.
    """

    def __init__(self) -> None:
        self.builders: List[PredicateBuilder] = [
            DateTimePredicateBuilder(),
            StringArrayPredicateBuilder(),
            BoolPredicateBuilder(),
            PlainPredicateBuilder(),
        ]

    def get_builder(self, filter_field: FilterField) -> Optional[PredicateBuilder]:
        """
        Returns a predicate builder that supports the given filter field.
        """
        for builder in self.builders:
            if builder.supports(filter_field):
                logger.debug(
                    "Selected builder %s for filter_field %s",
                    builder.__class__.__name__,
                    filter_field,
                )
                return builder
        logger.warning("No predicate builder found for filter_field: %s", filter_field)
        return None
