import os
import tempfile
import unittest

from app.managers.file_management.file_manager import FileManager
from app.schemas.file_filter import (
    FileFilterModel,
    FilterField,
    FilterFieldDatetime,
    FilterFieldStringArray,
    FilterMatchMode,
    OrderingModel,
    SearchModel,
    SortDirection,
)
from app.services.detection.detection_file_service import DetectionFileService
from app.services.file_management.file_filter_service import FileFilterService


class TestDetectionFileService(unittest.TestCase):
    def make_service(self, root_dir: str, cache_dir: str) -> DetectionFileService:
        filter_service = FileFilterService()
        return DetectionFileService(
            root_directory=root_dir,
            cache_dir=cache_dir,
            file_manager=FileManager(filter_service),
            filter_service=filter_service,
        )

    def make_model_filters(self) -> FileFilterModel:
        return FileFilterModel(
            type=FilterFieldStringArray(value=None, match_mode=FilterMatchMode.IN),
            file_suffixes=FilterFieldStringArray(
                value=["_ncnn_model", ".pt", ".tflite", ".hef", ".onnx"],
                match_mode=FilterMatchMode.IN,
            ),
            modified=FilterFieldDatetime(
                value=None,
                constraints=[
                    FilterField(
                        value=None,
                        match_mode=FilterMatchMode.DATE_AFTER,
                    ),
                    FilterField(
                        value=None,
                        match_mode=FilterMatchMode.DATE_BEFORE,
                    ),
                ],
                operator=None,
            ),
        )

    def test_search_filters_local_and_loadable_models(self):
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as cache_dir:
            open(os.path.join(root_dir, "local-sem.pt"), "w").close()
            open(os.path.join(root_dir, "unrelated-model.pt"), "w").close()
            service = self.make_service(root_dir, cache_dir)

            result = service.get_files_tree(
                filter_model=self.make_model_filters(),
                search=SearchModel(value="sem", field="name"),
                ordering=OrderingModel(
                    field="modified",
                    direction=SortDirection.desc,
                ),
            )

            names = [item.name for item in result.data]
            self.assertIn("local-sem.pt", names)
            self.assertIn("yolo26n-sem.pt", names)
            self.assertNotIn("unrelated-model.pt", names)
            self.assertNotIn("yolo26n.pt", names)

    def test_loadable_models_are_sorted_with_local_models(self):
        with tempfile.TemporaryDirectory() as root_dir, tempfile.TemporaryDirectory() as cache_dir:
            open(os.path.join(root_dir, "zz-local-model.pt"), "w").close()
            service = self.make_service(root_dir, cache_dir)

            result = service.get_files_tree(
                filter_model=self.make_model_filters(),
                ordering=OrderingModel(
                    field="name",
                    direction=SortDirection.asc,
                ),
            )

            names = [item.name for item in result.data]
            self.assertLess(names.index("yolo11n.pt"), names.index("zz-local-model.pt"))


if __name__ == "__main__":
    unittest.main()
