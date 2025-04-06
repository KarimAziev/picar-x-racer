import tempfile
import unittest
from pathlib import Path

from app.util.atomic_write import atomic_write


class TestAtomicWrite(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_atomic_write_text_mode(self):
        target_file = self.base_dir / "example.txt"
        temp_file = target_file.with_suffix(target_file.suffix + ".tmp")
        content = "Hello, atomic write!"

        self.assertFalse(target_file.exists())
        self.assertFalse(temp_file.exists())

        with atomic_write(target_file, mode="w") as f:
            f.write(content)

        self.assertTrue(target_file.exists())
        self.assertFalse(temp_file.exists())

        with open(target_file, "r") as f:
            self.assertEqual(f.read(), content)

    def test_atomic_write_binary_mode(self):
        target_file = self.base_dir / "image.png"
        temp_file = target_file.with_suffix(target_file.suffix + ".tmp")
        content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        self.assertFalse(target_file.exists())
        self.assertFalse(temp_file.exists())

        with atomic_write(target_file, mode="wb", encoding=None) as f:
            f.write(content)

        self.assertTrue(target_file.exists())
        self.assertFalse(temp_file.exists())

        with open(target_file, "rb") as f:
            self.assertEqual(f.read(), content)

    def test_atomic_write_exception_cleans_up_temp_file(self):
        target_file = self.base_dir / "fail.txt"
        temp_file = target_file.with_suffix(target_file.suffix + ".tmp")
        content = "This will fail."

        self.assertFalse(target_file.exists())
        self.assertFalse(temp_file.exists())

        with self.assertRaises(RuntimeError):
            with atomic_write(target_file, mode="w") as f:
                f.write(content)
                raise RuntimeError("Intentional Failure")

        self.assertFalse(target_file.exists())
        self.assertFalse(temp_file.exists())

    def test_atomic_write_creates_directory(self):

        new_dir = self.base_dir / "nonexistent" / "subdir"
        target_file = new_dir / "output.txt"
        temp_file = target_file.with_suffix(target_file.suffix + ".tmp")
        content = "Directory creation test."

        self.assertFalse(new_dir.exists())

        with atomic_write(target_file, mode="w") as f:
            f.write(content)

        self.assertTrue(new_dir.exists())
        self.assertTrue(target_file.exists())
        self.assertFalse(temp_file.exists())

        with open(target_file, "r") as f:
            self.assertEqual(f.read(), content)


if __name__ == "__main__":
    unittest.main()
