# Monkey patch for matplotlib.ft2font module:
# When using ultralytics, matplotlib is imported and its _check_versions
# function attempts to load the ft2font C-extension. On some systems during
# test discovery, this results in a segmentation fault
import sys
import types


class DummyFT2Font:
    def __init__(self, *args, **kwargs):
        pass

    def some_method(self, *args, **kwargs):
        pass


class DummyFT2Image:
    def __init__(self, *args, **kwargs):
        pass

    def some_image_method(self, *args, **kwargs):
        pass


class DummyKerning:
    DEFAULT = 0


DummyLoadFlags = 0

# Additional stubs for Python 3.9+
KERNING_DEFAULT = 0
LOAD_NO_HINTING = 0
LOAD_TARGET_LIGHT = 0

dummy_ft2font = types.ModuleType("matplotlib.ft2font")
dummy_ft2font.FT2Font = DummyFT2Font  # type: ignore
dummy_ft2font.FT2Image = DummyFT2Image  # type: ignore
dummy_ft2font.Kerning = DummyKerning  # type: ignore
dummy_ft2font.LoadFlags = DummyLoadFlags  # type: ignore
dummy_ft2font.KERNING_DEFAULT = KERNING_DEFAULT  # type: ignore
dummy_ft2font.LOAD_NO_HINTING = LOAD_NO_HINTING  # type: ignore
dummy_ft2font.LOAD_TARGET_LIGHT = LOAD_TARGET_LIGHT  # type: ignore

sys.modules["matplotlib.ft2font"] = dummy_ft2font


import os
import unittest
from typing import TYPE_CHECKING, Any, Dict, cast
from unittest.mock import MagicMock, patch

from app.config.config import settings
from app.managers.model_manager import ModelManager

if TYPE_CHECKING:
    from ultralytics import YOLO


class DummyYOLO:
    def __init__(self, *args, **kwargs):

        self.args = args
        self.kwargs: Dict[str, Any] = kwargs

    def __call__(self, *args, **kwargs) -> "DummyYOLO":
        return self


class TestModelManager(unittest.TestCase):
    def setUp(self):
        settings.YOLO_MODEL_EDGE_TPU_PATH = "fake_edge_tpu_path"
        settings.YOLO_MODEL_PATH = "fake_yolo_model_path"
        settings.DATA_DIR = "/dummy/data/dir"

    def tearDown(self):
        pass

    @patch(
        "app.managers.model_manager.resolve_absolute_path",
        lambda path, base: os.path.join(base, path),
    )
    @patch("ultralytics.YOLO", new=DummyYOLO)
    def test_custom_model_path_load_success(self):
        """Test that a custom provided model path is used and the model is loaded successfully."""
        custom_path = "custom_model.pt"
        manager = ModelManager(model_path=custom_path)
        expected_path = os.path.join(settings.DATA_DIR, custom_path)
        model, error = manager.__enter__()
        self.assertIsInstance(model, DummyYOLO)
        self.assertIsNone(error)
        model = cast("DummyYOLO", model)

        self.assertEqual(model.kwargs.get("model"), expected_path)
        self.assertEqual(model.kwargs.get("task"), "detect")
        manager.__exit__(None, None, None)
        self.assertFalse(hasattr(manager, "model"))

    @patch("app.managers.model_manager.resolve_absolute_path", lambda path, *_: path)
    @patch("app.managers.model_manager.os.path.exists")
    @patch("app.managers.model_manager.is_google_coral_connected")
    @patch("ultralytics.YOLO", new=DummyYOLO)
    def test_default_edge_tpu_path_load_success(
        self, mock_coral: MagicMock, mock_exists: MagicMock
    ):
        """
        Test that when no custom model_path is provided and the edge TPU model file exists
        (and Coral is connected), the YOLO_MODEL_EDGE_TPU_PATH is used.
        """
        manager = ModelManager()

        def fake_exists(path):
            if path == settings.YOLO_MODEL_EDGE_TPU_PATH:
                return True
            return False

        mock_exists.side_effect = fake_exists
        mock_coral.return_value = True

        model, error = manager.__enter__()
        self.assertEqual(manager.model_path, settings.YOLO_MODEL_EDGE_TPU_PATH)
        self.assertIsInstance(model, DummyYOLO)
        self.assertIsNone(error)
        manager.__exit__(None, None, None)

    @patch("app.managers.model_manager.resolve_absolute_path", lambda path, base: path)
    @patch("app.managers.model_manager.os.path.exists")
    @patch("app.managers.model_manager.is_google_coral_connected")
    @patch("ultralytics.YOLO", new=DummyYOLO)
    def test_default_yolo_model_path_load_success(
        self, mock_coral: MagicMock, mock_exists: MagicMock
    ):
        """
        Test that when no custom model_path is provided and edge TPU model file does not exist
        (or Coral is not connected), the default YOLO_MODEL_PATH is used.
        """
        manager = ModelManager()

        def fake_exists(path):
            if path == settings.YOLO_MODEL_EDGE_TPU_PATH:
                return False
            return True

        mock_exists.side_effect = fake_exists
        mock_coral.return_value = False

        model, error = manager.__enter__()
        self.assertEqual(manager.model_path, settings.YOLO_MODEL_PATH)
        self.assertIsInstance(model, DummyYOLO)
        self.assertIsNone(error)
        manager.__exit__(None, None, None)

    @patch("app.managers.model_manager.logger.error")
    @patch("app.managers.model_manager.resolve_absolute_path", lambda path, base: path)
    @patch("ultralytics.YOLO")
    def test_file_not_found_error(self, mock_yolo, _: MagicMock):
        """
        Test that if YOLO initialization raises a FileNotFoundError,
        the error message is correctly set.
        """
        mock_yolo.side_effect = FileNotFoundError("dummy file not found")
        custom_path = "nonexistent_model.pt"
        manager = ModelManager(model_path=custom_path)

        model, error = manager.__enter__()
        self.assertIsNone(model)
        expected_error = f"Model's file {custom_path} is not found"
        self.assertEqual(error, expected_error)
        manager.__exit__(None, None, None)

    @patch("app.managers.model_manager.resolve_absolute_path", lambda path, base: path)
    @patch("ultralytics.YOLO")
    def test_unexpected_exception(self, mock_yolo: MagicMock):
        """
        Test that if YOLO initialization raises an unexpected Exception,
        the error message is correctly set.
        """
        with patch("app.managers.model_manager.logger.error") as mock_logger_error:
            mock_yolo.side_effect = Exception("unexpected")
            custom_path = "unexpected_error_model.pt"
            manager = ModelManager(model_path=custom_path)
            model, error = manager.__enter__()
            self.assertIsNone(model)
            expected_error = f"Unexpected error while loading {custom_path}"
            self.assertEqual(error, expected_error)
            manager.__exit__(None, None, None)
            mock_logger_error.assert_called_once()

    @patch("app.managers.model_manager.resolve_absolute_path", lambda path, base: path)
    @patch("ultralytics.YOLO")
    def test_keyboard_interrupt_handling(self, mock_yolo: MagicMock):
        """
        Test that if a KeyboardInterrupt is raised during model loading,
        the __enter__ method returns the expected message.
        """
        mock_yolo.side_effect = KeyboardInterrupt
        manager = ModelManager(model_path="interrupt_model.pt")
        model, error = manager.__enter__()
        self.assertIsNone(model)
        self.assertEqual(error, "Detection model context received KeyboardInterrupt.")
        manager.__exit__(None, None, None)

    def test_exit_cleanup_with_exception(self):
        """
        Test that __exit__ logs (or processes) an exception and deletes the model attribute.
        (We use a dummy model and pass fake exception info.)
        """
        manager = ModelManager(model_path="dummy.pt")
        dummy_model = cast("YOLO", DummyYOLO())

        manager.model = dummy_model
        exc_type = ValueError
        exc_value = ValueError("dummy error")
        manager.__exit__(exc_type, exc_value, None)
        self.assertFalse(hasattr(manager, "model"))


if __name__ == "__main__":
    unittest.main()
