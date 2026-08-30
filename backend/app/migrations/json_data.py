from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

JsonObject = Dict[str, Any]
Migration = Callable[[JsonObject], JsonObject]
Validator = Callable[[JsonObject], object]


class JsonDataMigrationError(ValueError):
    """Raised when a JSON document cannot be migrated safely."""


@dataclass(frozen=True)
class MigrationResult:
    data: JsonObject
    from_version: int
    to_version: int
    applied_versions: Tuple[int, ...]

    @property
    def changed(self) -> bool:
        return bool(self.applied_versions)


class JsonDataMigrator:
    """Apply ordered, versioned migrations to a JSON object."""

    def __init__(
        self,
        migrations: Mapping[int, Migration],
        *,
        version_field: str = "schema_version",
        validator: Optional[Validator] = None,
    ) -> None:
        self._migrations = dict(migrations)
        self.version_field = version_field
        self._validator = validator
        self.latest_version = max(self._migrations, default=0)

    def migrate(self, source: JsonObject) -> MigrationResult:
        data = deepcopy(source)
        from_version = self._read_version(data)

        if from_version > self.latest_version:
            raise JsonDataMigrationError(
                f"JSON schema version {from_version} is newer than supported "
                f"version {self.latest_version}"
            )

        applied_versions: list[int] = []
        for target_version in range(from_version + 1, self.latest_version + 1):
            migration = self._migrations.get(target_version)
            if migration is None:
                raise JsonDataMigrationError(
                    f"Missing JSON migration for version {target_version}"
                )
            data = migration(data)
            if not isinstance(data, dict):
                raise JsonDataMigrationError(
                    f"JSON migration {target_version} did not return an object"
                )
            data[self.version_field] = target_version
            applied_versions.append(target_version)

        if self._validator:
            self._validator(data)

        return MigrationResult(
            data=data,
            from_version=from_version,
            to_version=self.latest_version,
            applied_versions=tuple(applied_versions),
        )

    def _read_version(self, data: JsonObject) -> int:
        version = data.get(self.version_field, 0)
        if isinstance(version, bool) or not isinstance(version, int) or version < 0:
            raise JsonDataMigrationError(
                f"'{self.version_field}' must be a non-negative integer"
            )
        return version
