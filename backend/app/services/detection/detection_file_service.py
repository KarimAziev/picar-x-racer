import os
from typing import Optional, Set

from app.schemas.file_filter import (
    FileFilterModel,
    FileResponseModel,
    FilterInfo,
    GroupedFile,
    OrderingModel,
    SearchModel,
    ValueLabelOption,
)
from app.services.file_management.file_manager_service import FileManagerService

GITHUB_ASSETS_NAMES = (
    [
        f"yolov8{k}{suffix}.pt"
        for k in "nsmlx"
        for suffix in ("", "-cls", "-seg", "-pose", "-obb", "-oiv7")
    ]
    + [
        f"yolo11{k}{suffix}.pt"
        for k in "nsmlx"
        for suffix in ("", "-cls", "-seg", "-pose", "-obb")
    ]
    + [f"yolo12{k}{suffix}.pt" for k in "nsmlx" for suffix in ("",)]
    + [f"yolov5{k}{resolution}u.pt" for k in "nsmlx" for resolution in ("", "6")]
    + [f"yolov3{k}u.pt" for k in ("", "-spp", "-tiny")]
    + [f"yolov8{k}-world.pt" for k in "smlx"]
    + [f"yolov8{k}-worldv2.pt" for k in "smlx"]
    + [f"yolov9{k}.pt" for k in "tsmce"]
    + [f"yolov10{k}.pt" for k in "nsmblx"]
    + [f"yolo_nas_{k}.pt" for k in "sml"]
    + [f"sam_{k}.pt" for k in "bl"]
    + [f"FastSAM-{k}.pt" for k in "sx"]
    + [f"rtdetr-{k}.pt" for k in "lx"]
    + ["mobile_sam.pt"]
    + ["calibration_image_sample_data_20x128x128x3_float32.npy.zip"]
)


class DetectionFileService(FileManagerService):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def get_files_tree(
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

        result = super().get_files_tree(
            filter_model=filter_model, search=search, ordering=ordering, subdir=subdir
        )
        result.filter_info = FilterInfo(
            type=result.filter_info.type,
            file_suffixes=[
                ValueLabelOption(value=item, label=item)
                for item in ["_ncnn_model", ".pt", ".tflite", ".hef", ".onnx"]
            ],
        )

        if result.dir is None:
            loaded_models: Set[str] = set()
            for file in os.listdir(self.root_directory):
                loaded_models.add(file)

            for key in GITHUB_ASSETS_NAMES:
                if (
                    not key.endswith(("-cls.pt", "-seg.pt", ".npy.pt", "-obb.pt"))
                    and not key in loaded_models
                ):
                    detail = GroupedFile(
                        name=key,
                        size=0,
                        type="loadable",
                        is_dir=False,
                        path=key,
                        modified=None,
                    )
                    result.data.append(detail)

        return result
