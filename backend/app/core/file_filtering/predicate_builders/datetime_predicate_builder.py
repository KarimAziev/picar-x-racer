import datetime
import zoneinfo
from typing import Callable, Optional

from app.core.file_filtering.predicate_builders.base_predicate_builder import (
    PredicateBuilder,
)
from app.core.logger import Logger
from app.schemas.file_filter import FileDetail, Filter, FilterFieldDatetime

_log = Logger(__name__)


class DateTimePredicateBuilder(PredicateBuilder):
    def supports(self, filter_field: Filter) -> bool:
        return isinstance(filter_field, FilterFieldDatetime)

    def build(
        self, filter_field: FilterFieldDatetime, field_name: str
    ) -> Callable[[FileDetail], bool]:
        start_date, end_date = filter_field.date_range()

        def datetime_predicate(f: FileDetail) -> bool:
            value: Optional[float] = getattr(f, field_name)
            if value is None:
                return False
            mod_dt = datetime.datetime.fromtimestamp(
                value, tz=zoneinfo.ZoneInfo("UTC")
            ).replace(tzinfo=None)
            if start_date or end_date:
                _log.debug(
                    "datetime_predicate: value %s, start_date=%s, end_date=%s, mod_dt=%s, filter_field=%s",
                    value,
                    start_date,
                    end_date,
                    mod_dt,
                    filter_field,
                )
            if start_date and mod_dt < start_date:
                return False
            if end_date and mod_dt > end_date:
                return False
            return True

        return datetime_predicate
