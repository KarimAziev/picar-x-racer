import os
from typing import List, Optional, Set

from app.schemas.file_filter import (
    FileDetail,
    FileFilterModel,
    FileResponseModel,
    FilterInfo,
    OrderingModel,
    SearchModel,
    ValueLabelOption,
)
from app.services.file_manager_service import FileManagerService
from ultralytics.utils.downloads import GITHUB_ASSETS_NAMES


class DetectionFileService(FileManagerService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_files(
        self,
        filter_model: Optional[FileFilterModel] = None,
        search: Optional[SearchModel] = None,
        ordering: Optional[OrderingModel] = None,
        subdir: Optional[str] = None,
    ) -> FileResponseModel:
        """
        Walk the directory tree and apply searching, filtering, and ordering.
        Finally, group the results by their directories.
        """
        result = super().get_files(
            filter_model=filter_model, search=search, ordering=ordering, subdir=subdir
        )
        result.filter_info = FilterInfo(
            type=result.filter_info.type,
            file_suffixes=[
                ValueLabelOption(value=item, label=item)
                for item in ["_ncnn_model", ".pt", ".tflite", ".hef", ".onnx"]
            ],
        )
        return result

    def list_files(self, subdir: Optional[str] = None) -> List[FileDetail]:

        files = super().list_files(subdir=subdir)
        print("files", files[0])

        if subdir is None:
            loaded_models: Set[str] = set()
            for file in os.listdir(self.root_directory):
                loaded_models.add(file)

            for key in GITHUB_ASSETS_NAMES:
                if (
                    not key.endswith(("-cls.pt", "-seg.pt", ".npy.pt", "-obb.pt"))
                    and not key in loaded_models
                ):
                    detail = FileDetail(
                        name=key,
                        size=0,
                        type="loadable",
                        is_dir=False,
                        path=key,
                        modified=None,
                    )
                    files.append(detail)

        return files
