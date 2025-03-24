from __future__ import annotations

from typing import Callable, List, Optional

from app.core.file_filtering.predicate_builder_factory import PredicateBuilderFactory
from app.core.file_filtering.predicate_builders.suffix_predicate_builder import (
    SuffixPredicateBuilder,
)
from app.core.logger import Logger
from app.schemas.file_filter import FileDetail, FileFilterModel, SearchModel
from rapidfuzz import fuzz

_log = Logger(name=__name__)


class FileFilterService:
    def __init__(self) -> None:
        self.factory = PredicateBuilderFactory()

        self.special_predicate_builders = {
            "file_suffixes": SuffixPredicateBuilder(),
        }

    def _build_search_predicate(
        self,
        search: Optional[SearchModel] = None,
        min_search_score=70,
    ) -> Optional[Callable[[FileDetail], bool]]:
        if search and search.value:
            search_field = search.field or "name"
            search_val = search.value.lower()

            def fuzzy_predicate(f: FileDetail) -> bool:
                value = getattr(f, search_field, "").lower()
                score = fuzz.WRatio(search_val, value)
                return score >= min_search_score

            return fuzzy_predicate
        return None

    def _build_filter_predicates(
        self,
        filter_model: Optional[FileFilterModel] = None,
        search: Optional[SearchModel] = None,
        min_search_score=70,
    ) -> List[Callable[[FileDetail], bool]]:
        predicates: List[Callable[[FileDetail], bool]] = []

        search_pred = self._build_search_predicate(
            search=search, min_search_score=min_search_score
        )
        if search_pred:
            predicates.append(search_pred)

        if not filter_model:
            return predicates

        filter_dict = filter_model.model_dump(exclude_none=True)

        for field_name in filter_dict.keys():
            filter_field = getattr(filter_model, field_name)

            special_builder = self.special_predicate_builders.get(field_name)

            if special_builder:
                predicate = special_builder.build(filter_field, field_name)
                predicates.append(predicate)
            else:
                builder = self.factory.get_builder(filter_field)
                if builder:
                    predicate = builder.build(filter_field, field_name)
                    predicates.append(predicate)
                else:
                    _log.warning("No builder could handle field: %s", field_name)

        return predicates

    def filter_files(
        self,
        files: List[FileDetail],
        filter_model: Optional[FileFilterModel] = None,
        search: Optional[SearchModel] = None,
        min_search_score=70,
        filtered_file_transformer: Optional[Callable[[FileDetail], FileDetail]] = None,
    ) -> List[FileDetail]:
        """
        Walk the directory tree and apply searching and filtering.

        In addition to returning files that match the predicates, include any parent
        directories (from the full input files list) of any matched file.
        """
        predicates = self._build_filter_predicates(
            filter_model=filter_model, search=search, min_search_score=min_search_score
        )

        if filtered_file_transformer:
            matched = [
                filtered_file_transformer(f)
                for f in files
                if all(pred(f) for pred in predicates)
            ]
        else:
            matched = [f for f in files if all(pred(f) for pred in predicates)]

        dir_map = {f.path: f for f in files if f.is_dir}

        def get_parent_paths(path: str) -> List[str]:
            parents = []
            parts = path.split("/")
            for i in range(1, len(parts)):
                parent_path = "/".join(parts[:i])
                parents.append(parent_path)
            return parents

        additional_dirs = {}
        for file_detail in matched:
            if not file_detail.is_dir:
                for parent in get_parent_paths(file_detail.path):
                    if parent in dir_map:
                        additional_dirs[parent] = dir_map[parent]

        final_set = {f.path: f for f in matched}
        final_set.update(additional_dirs)

        return list(final_set.values())
