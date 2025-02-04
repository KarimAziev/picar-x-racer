import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.managers.json_data_manager import JsonDataManager


class TestJsonDataManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

        self.target_file = self.base_dir / "target.json"
        self.template_file = self.base_dir / "template.json"

        self.template_data = {"default": True, "value": 0}
        with open(self.template_file, "w") as f:
            json.dump(self.template_data, f)

        if self.target_file.exists():
            self.target_file.unlink()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_source_file_uses_template_when_target_missing(self):
        """Test that when the target file does not exist, source_file should point to the template."""
        manager = JsonDataManager(str(self.target_file), str(self.template_file))
        self.assertEqual(manager.source_file, str(self.template_file))
        data = manager.load_data()
        self.assertEqual(data, self.template_data)

    def test_source_file_uses_target_when_exists(self):
        target_data = {"updated": True, "value": 42}
        with open(self.target_file, "w") as f:
            json.dump(target_data, f)

        manager = JsonDataManager(str(self.target_file), str(self.template_file))

        self.assertEqual(manager.source_file, str(self.target_file))

        data = manager.load_data()
        self.assertEqual(data, target_data)

    def test_update_writes_to_target_and_emits_event(self):
        manager = JsonDataManager(str(self.target_file), str(self.template_file))

        manager.emit = MagicMock()

        new_data = {"message": "Hello, world!", "count": 100}

        updated = manager.update(new_data)

        self.assertEqual(updated, new_data)
        self.assertEqual(manager._cache, new_data)
        with open(self.target_file, "r") as f:
            file_data = json.load(f)
        self.assertEqual(file_data, new_data)

        manager.emit.assert_called_with(JsonDataManager.UPDATE_EVENT, new_data)

    def test_merge_updates_existing_data_and_emits_event(self):
        initial_data = {"a": 1, "b": 2}
        with open(self.target_file, "w") as f:
            json.dump(initial_data, f)
        time.sleep(0.1)

        manager = JsonDataManager(str(self.target_file), str(self.template_file))
        manager.emit = MagicMock()
        partial_data = {"b": 20, "c": 3}
        merged_data = manager.merge(partial_data)

        expected = {"a": 1, "b": 20, "c": 3}
        self.assertEqual(merged_data, expected)
        self.assertEqual(manager._cache, expected)

        with open(self.target_file, "r") as f:
            file_data = json.load(f)
        self.assertEqual(file_data, expected)

        manager.emit.assert_called_with(JsonDataManager.UPDATE_EVENT, expected)

    def test_load_data_uses_cache_and_reloads_after_external_change(self):
        target_data = {"initial": True}
        with open(self.target_file, "w") as f:
            json.dump(target_data, f)

        manager = JsonDataManager(str(self.target_file), str(self.template_file))
        manager.emit = MagicMock()
        data1 = manager.load_data()
        self.assertEqual(data1, target_data)

        updated_target_data = {"initial": False, "changed": True}
        with open(self.target_file, "w") as f:
            json.dump(updated_target_data, f)

        new_ts = os.path.getmtime(self.target_file) + 1
        os.utime(self.target_file, (new_ts, new_ts))

        import time

        time.sleep(0.1)

        # When load_data is called again, it should detect the mtime change and reload.
        data2 = manager.load_data()
        self.assertEqual(data2, updated_target_data)
        manager.emit.assert_called_with(JsonDataManager.LOAD_EVENT, updated_target_data)


if __name__ == "__main__":
    unittest.main()
