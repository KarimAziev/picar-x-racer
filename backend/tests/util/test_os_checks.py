import unittest
from unittest.mock import Mock, mock_open, patch

from app.util.os_checks import get_gpio_factory_name, is_raspberry_pi


class TestOSChecks(unittest.TestCase):
    def tearDown(self):
        is_raspberry_pi.cache_clear()
        get_gpio_factory_name.cache_clear()

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

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"Raspberry Pi 5 Model B Rev 1.0\x00",
    )
    def test_get_gpio_factory_name_rpi5(self, mock_file: Mock, mock_exists):
        """Test that get_gpio_factory_name returns 'lgpio' for a Raspberry Pi 5."""
        result = get_gpio_factory_name()
        self.assertEqual(result, "lgpio")
        mock_exists.assert_called_once_with("/proc/device-tree/model")
        mock_file.assert_called_once_with("/proc/device-tree/model", "rb")

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"Raspberry Pi Model B Rev 1.2\x00",
    )
    def test_get_gpio_factory_name_rpigpio(self, mock_file: Mock, mock_exists):
        """Test that get_gpio_factory_name returns 'rpigpio' for a non-5 Raspberry Pi."""
        result = get_gpio_factory_name()
        self.assertEqual(result, "rpigpio")
        mock_exists.assert_called_once_with("/proc/device-tree/model")
        mock_file.assert_called_once_with("/proc/device-tree/model", "rb")

    @patch("os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"Some unknown model\x00",
    )
    def test_get_gpio_factory_name_no_match(self, mock_file: Mock, mock_exists):
        """
        Test that get_gpio_factory_name returns 'mock' when the model file exists
        but does not contain a recognizable Raspberry Pi model.
        """
        result = get_gpio_factory_name()
        self.assertEqual(result, "mock")
        mock_exists.assert_called_once_with("/proc/device-tree/model")
        mock_file.assert_called_once_with("/proc/device-tree/model", "rb")

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=Exception("read error"))
    def test_get_gpio_factory_name_exception(self, mock_file: Mock, mock_exists):
        """
        Test that get_gpio_factory_name returns 'mock' when an exception is raised
        during file reading.
        """
        result = get_gpio_factory_name()
        self.assertEqual(result, "mock")
        mock_exists.assert_called_once_with("/proc/device-tree/model")
        mock_file.assert_called_once_with("/proc/device-tree/model", "rb")

    @patch("os.path.exists", return_value=False)
    def test_get_gpio_factory_name_file_not_exist(self, mock_exists):
        """
        Test that get_gpio_factory_name returns 'mock' when the model file does not exist.
        """
        result = get_gpio_factory_name()
        self.assertEqual(result, "mock")
        mock_exists.assert_called_once_with("/proc/device-tree/model")


if __name__ == "__main__":
    unittest.main()
