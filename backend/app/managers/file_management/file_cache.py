from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

from app.core.logger import Logger
from app.util.atomic_write import atomic_write

T = TypeVar("T")

_log = Logger(__name__)


@dataclass
class CacheEntry(Generic[T]):
    modified_time: float
    details: T


T = TypeVar("T")


class CacheManager(Generic[T]):
    def __init__(
        self,
        cache_file: str,
        details_factory: Callable[[Dict[str, Any]], T],
    ) -> None:
        """
        details_factory: a function that converts a dict (from JSON)
                         into an instance of type T.
        """
        self.cache_file: str = cache_file
        self.details_factory: Callable[[Dict[str, Any]], T] = details_factory
        self._cache: Optional[Dict[str, CacheEntry[T]]] = None
        self._dirty: bool = False

    def get_cache(self) -> Dict[str, CacheEntry[T]]:
        if self._cache is not None:
            return self._cache

        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    loaded: Dict[str, Any] = json.load(f)
                    self._cache = {
                        key: CacheEntry(
                            modified_time=value["modified_time"],
                            details=self.details_factory(value["details"]),
                        )
                        for key, value in loaded.items()
                    }
            except Exception:
                _log.error(
                    "Unhandled error loading cache from %s",
                    self.cache_file,
                    exc_info=True,
                )
                self._cache = {}
        else:
            self._cache = {}
        return self._cache

    def mark_dirty(self) -> None:
        self._dirty = True

    def maybe_save(self) -> None:
        if self._dirty:
            self.save_cache()
            self._dirty = False

    def save_cache(self) -> None:
        if self._cache is None:
            return

        serializable: Dict[str, Any] = {k: asdict(v) for k, v in self._cache.items()}
        try:
            with atomic_write(self.cache_file, mode="w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
            _log.info(f"Cache saved to {self.cache_file}")
        except Exception as e:
            _log.error(f"Error saving cache: {e}")
