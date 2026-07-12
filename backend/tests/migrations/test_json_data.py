import unittest

from app.migrations.json_data import JsonDataMigrationError, JsonDataMigrator


class TestJsonDataMigrator(unittest.TestCase):
    def test_applies_migrations_in_version_order(self):
        applied = []

        def migrate_v1(data):
            applied.append(1)
            data["first"] = True
            return data

        def migrate_v2(data):
            applied.append(2)
            data["second"] = data["first"]
            return data

        result = JsonDataMigrator({1: migrate_v1, 2: migrate_v2}).migrate({})

        self.assertEqual(applied, [1, 2])
        self.assertEqual(result.applied_versions, (1, 2))
        self.assertEqual(result.data["schema_version"], 2)
        self.assertTrue(result.data["second"])

    def test_does_not_mutate_source_data(self):
        source = {"nested": {"value": 1}}

        def migrate_v1(data):
            data["nested"]["value"] = 2
            return data

        result = JsonDataMigrator({1: migrate_v1}).migrate(source)

        self.assertEqual(source, {"nested": {"value": 1}})
        self.assertEqual(result.data["nested"], {"value": 2})

    def test_rejects_newer_schema_version(self):
        migrator = JsonDataMigrator({1: lambda data: data})

        with self.assertRaisesRegex(JsonDataMigrationError, "newer than supported"):
            migrator.migrate({"schema_version": 2})

    def test_rejects_missing_migration(self):
        migrator = JsonDataMigrator({2: lambda data: data})

        with self.assertRaisesRegex(JsonDataMigrationError, "version 1"):
            migrator.migrate({})

    def test_validates_after_migration(self):
        validated = []
        migrator = JsonDataMigrator(
            {1: lambda data: data}, validator=lambda data: validated.append(data)
        )

        migrator.migrate({})

        self.assertEqual(validated[0]["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
