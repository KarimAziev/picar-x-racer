import unittest
from unittest.mock import Mock, mock_open, patch

from app.util.os_checks import is_raspberry_pi


class TestOSChecks(unittest.TestCase):
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="Raspberry Pi Model B Rev 1.2",
    )
    def test_is_raspberry_pi_true(self, mock_file: Mock):
        """Test when the system is a Raspberry Pi."""
        result = is_raspberry_pi()
        self.assertTrue(result)
        mock_file.assert_called_once_with("/proc/device-tree/model", "r")

    @patch("builtins.open", new_callable=mock_open, read_data="Some other model")
    def test_is_raspberry_pi_false(self, mock_file: Mock):
        """Test when the system is not a Raspberry Pi."""
        result = is_raspberry_pi()
        self.assertFalse(result)
        mock_file.assert_called_once_with("/proc/device-tree/model", "r")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_is_raspberry_pi_file_not_found(self, mock_file: Mock):
        """Test when the model file does not exist."""
        result = is_raspberry_pi()
        self.assertFalse(result)
        mock_file.assert_called_once_with("/proc/device-tree/model", "r")

    def tearDown(self):
        is_raspberry_pi.cache_clear()


if __name__ == "__main__":
    unittest.main()
