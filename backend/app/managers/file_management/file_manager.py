from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from app.core.logger import Logger
from app.exceptions.file_exceptions import InvalidFileName
from app.schemas.file_filter import (
    FileDetail,
    FileFilterModel,
    FileFlatResponseModel,
    FileResponseModel,
    FilterInfo,
    GroupedFile,
    OrderingModel,
    SearchModel,
    SortDirection,
    ValueLabelOption,
)
from app.schemas.file_management import BatchFileResult
from app.services.file_management.file_filter_service import FileFilterService
from app.util.atomic_write import atomic_write
from app.util.file_util import (
    abbreviate_path,
    exclude_nested_files,
    expand_home_dir,
    file_name_parent_directory,
    file_to_relative,
    resolve_absolute_path,
)
from app.util.mime_type_helper import guess_mime_type
from fastapi import UploadFile

_log = Logger(name=__name__)


class FileManager:
    file_types: List[ValueLabelOption] = [
        ValueLabelOption(value=item, label=item.title())
        for item in [
            "audio",
            "image",
            "text",
            "video",
            "application",
            "font",
            "example",
            "message",
            "model",
            "multipart",
        ]
    ]

    def __init__(self) -> None:
        self.filter_service = FileFilterService()

    def rename_file(self, filename: str, new_name: str) -> None:
        if not filename:
            raise InvalidFileName("Invalid filename")
        file_path = Path(filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File '{filename}' does not exist")

        if not new_name:
            raise InvalidFileName(f"Invalid filename for renaming '%s'", filename)

        parent_dir = Path(file_name_parent_directory(new_name))

        parent_dir.mkdir(parents=True, exist_ok=True)
        file_path.replace(new_name)

    def remove_file(self, filename: str) -> bool:
        if not filename:
            raise InvalidFileName("Invalid filename")

        file_path = Path(filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File '{filename}' does not exist")
        elif file_path.is_dir():
            shutil.rmtree(file_path)
            return True
        else:
            file_path.unlink()
            return True

    def batch_remove_files(
        self, filenames: List[str]
    ) -> Tuple[List[BatchFileResult], List[Dict[str, str]]]:
        filtered_files = exclude_nested_files(filenames)
        responses: List[BatchFileResult] = []
        success_responses: List[Dict[str, str]] = []

        for file_path in filtered_files:
            filename = file_path.as_posix()
            relative_name = file_path.name
            _log.info("Removing file '%s'", filename)
            result = False
            error: Optional[str] = None
            try:
                shutil.rmtree(file_path) if file_path.is_dir() else file_path.unlink()
                result = not file_path.exists()
            except FileNotFoundError:
                error = "File not found"
                _log.warning("Failed to remove file %s: not found", filename)
            except Exception:
                error = "Internal server error"
                _log.error(
                    f"Unhandled error while removing file '{filename}'",
                    exc_info=True,
                )
            finally:
                responses.append(
                    BatchFileResult(
                        **{"success": result, "filename": relative_name, "error": error}
                    )
                )
                if result:
                    success_responses.append({"file": relative_name})

        return responses, success_responses

    def batch_move_files(
        self, filenames: List[str], target_dir: str
    ) -> Tuple[List[BatchFileResult], List[Dict[str, str]]]:

        if not os.path.isdir(target_dir) and os.path.exists(target_dir):
            target_dir = file_name_parent_directory(target_dir).as_posix()

        filtered_files = exclude_nested_files(filenames)
        responses: List[BatchFileResult] = []
        success_responses: List[Dict[str, str]] = []

        target_dir_path = Path(target_dir)

        target_dir_path.parent.mkdir(exist_ok=True, parents=True)

        for file_path in filtered_files:
            filename = file_path.as_posix()
            relative_name = file_path.name
            new_name = os.path.join(target_dir, os.path.basename(relative_name))
            _log.info(
                "Moving file '%s' to '%s' as '%s'", filename, target_dir, new_name
            )
            result = False
            error: Optional[str] = None
            try:
                file_path.replace(new_name)
                result = os.path.exists(new_name)
            except FileNotFoundError:
                error = "File not found"
                _log.warning("Failed to move file '%s': not found", filename)
            except Exception:
                error = "Internal server error"
                _log.error(
                    f"Unhandled error while moving file '{filename}'",
                    exc_info=True,
                )
            finally:
                responses.append(
                    BatchFileResult(
                        **{"success": result, "filename": relative_name, "error": error}
                    )
                )
                if result:
                    success_responses.append(
                        {
                            "file": relative_name,
                            "msg": f"'{relative_name}' to {abbreviate_path(target_dir)}",
                        }
                    )

        return responses, success_responses

    def _file_to_model(
        self, full_path: str, root_dir: Optional[str] = None
    ) -> FileDetail:
        """
        Constructs a FileDetail object from the provided full file path by gathering the file's metadata.
        """
        name = os.path.basename(full_path)
        stat_info = os.stat(full_path)
        is_directory = os.path.isdir(full_path)
        if not is_directory:
            guessed_content = guess_mime_type(full_path)
            content_type = guessed_content or "application/octet-stream"
            file_type = (
                content_type.split("/").pop(0) if content_type is not None else None
            )
        else:
            content_type = "directory"
            file_type = "directory"

        relative_path = file_to_relative(full_path, root_dir) if root_dir else full_path
        return FileDetail(
            name=name,
            path=relative_path,
            size=stat_info.st_size if not is_directory else 0,
            is_dir=is_directory,
            modified=stat_info.st_mtime,
            type=file_type,
            content_type=content_type,
            duration=None,
        )

    def list_files_recursively(
        self, root_dir: str, subdir: Optional[str] = None
    ) -> List[FileDetail]:
        """
        Recursively lists all files and directories from the specified subdirectory (or
        the root directory if none is provided), returning their file metadata as a list
        of FileDetail objects.
        """
        files: List[FileDetail] = []

        dir = os.path.join(root_dir, subdir) if subdir is not None else root_dir

        for dirpath, dirnames, filenames in os.walk(dir):
            relative_dir = os.path.relpath(dirpath, dir)
            if relative_dir == ".":
                relative_dir = ""

            for name in dirnames + filenames:
                full_path = os.path.join(dirpath, name)
                detail = self._file_to_model(full_path, root_dir)
                files.append(detail)

        return files

    def list_files(
        self, root_dir: str, subdir: Optional[str] = None, relative_path=False
    ) -> List[FileDetail]:
        """
        Lists all files and directories from the specified subdirectory (or
        the root directory if none is provided), returning their file metadata as a list
        of FileDetail objects.
        """
        if root_dir.startswith("~"):
            root_dir = os.path.expanduser(root_dir)

        if not os.path.exists(root_dir):
            return []

        files: List[FileDetail] = []
        directory = os.path.join(root_dir, subdir) if subdir is not None else root_dir
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            detail = (
                self._file_to_model(full_path, root_dir)
                if relative_path
                else self._file_to_model(full_path)
            )
            files.append(detail)
        return files

    def sort_files(
        self, files: List[FileDetail], ordering: Optional[OrderingModel] = None
    ):
        """
        Sorts the provided list of file details objects by applying an ordering based on
        the specified field and direction.

        If no ordering is provided, the original list order is maintained.
        """
        if ordering and ordering.field:
            files_len = len(files)
            field = ordering.field
            reverse = ordering.direction == SortDirection.desc
            try:
                files.sort(
                    key=lambda x: getattr(x, field) or files_len, reverse=reverse
                )
            except AttributeError:
                pass

        return files

    def get_files_in_dir(
        self,
        root_dir: str,
        subdir: Optional[str] = None,
        filter_model: Optional[FileFilterModel] = None,
        search: Optional[SearchModel] = None,
        ordering: Optional[OrderingModel] = None,
        filtered_file_transformer: Optional[Callable[[FileDetail], FileDetail]] = None,
    ) -> FileResponseModel:
        """
        Walk the directory tree and apply searching, filtering, and ordering.

        Finally, group the results by their directories.
        """
        root_dir = expand_home_dir(root_dir)
        all_files = self.list_files(root_dir, subdir)
        filtered_files = self.sort_files(
            self.filter_service.filter_files(
                all_files,
                filter_model=filter_model,
                search=search,
                filtered_file_transformer=filtered_file_transformer,
            ),
            ordering,
        )

        grouped_files = self.group_files(filtered_files)

        filter_info = FilterInfo(type=self.file_types)

        return FileResponseModel(
            data=grouped_files,
            filter_info=filter_info,
            dir=subdir,
            root_dir=abbreviate_path(root_dir),
        )

    def get_files_tree(
        self,
        root_dir: str,
        subdir: Optional[str] = None,
        filter_model: Optional[FileFilterModel] = None,
        search: Optional[SearchModel] = None,
        ordering: Optional[OrderingModel] = None,
        filtered_file_transformer: Optional[Callable[[FileDetail], FileDetail]] = None,
    ) -> FileResponseModel:
        """
        Walk the directory tree and apply searching, filtering, and ordering.

        Finally, group the results by their directories.
        """
        root_dir = expand_home_dir(root_dir)
        all_files = self.list_files_recursively(root_dir, subdir)
        filtered_files = self.sort_files(
            self.filter_service.filter_files(
                all_files,
                filter_model=filter_model,
                search=search,
                filtered_file_transformer=filtered_file_transformer,
            ),
            ordering,
        )

        grouped_files = self.group_files(filtered_files)

        filter_info = FilterInfo(type=self.file_types)

        return FileResponseModel(
            data=grouped_files,
            filter_info=filter_info,
            dir=subdir,
            root_dir=abbreviate_path(root_dir),
        )

    def get_files_flat(
        self,
        root_dir: str,
        subdir: Optional[str] = None,
        filter_model: Optional[FileFilterModel] = None,
        search: Optional[SearchModel] = None,
        ordering: Optional[OrderingModel] = None,
        filtered_file_transformer: Optional[Callable[[FileDetail], FileDetail]] = None,
    ) -> FileFlatResponseModel:
        """
        Walk the directory tree and apply searching, filtering, and ordering.
        """
        root_dir = expand_home_dir(root_dir)
        all_files = self.list_files_recursively(root_dir, subdir)
        filtered_files = self.sort_files(
            self.filter_service.filter_files(
                all_files,
                filter_model=filter_model,
                search=search,
                filtered_file_transformer=filtered_file_transformer,
            ),
            ordering,
        )

        filter_info = FilterInfo(type=self.file_types)

        return FileFlatResponseModel(
            data=filtered_files,
            filter_info=filter_info,
            dir=subdir,
            root_dir=abbreviate_path(root_dir),
        )

    def group_files(self, files: List[FileDetail]) -> List[GroupedFile]:
        """
        Group files and directories into a hierarchical tree.

        Directories are always placed before files within each folder.
        """
        nodes = {}
        order_map = {}
        for idx, f in enumerate(files):
            node = GroupedFile(**f.model_dump(), children=[] if f.is_dir else None)
            nodes[node.path] = node
            order_map[node.path] = idx

        roots = []
        for node in nodes.values():
            parent_path = os.path.dirname(node.path)
            if parent_path and parent_path in nodes:
                parent = nodes[parent_path]
                if parent.children is None:
                    parent.children = []
                parent.children.append(node)
            else:
                roots.append(node)

        def sort_children(node: GroupedFile):
            if node.children is not None and node.children:
                node.children.sort(
                    key=lambda child: (
                        0 if child.is_dir else 1,
                        order_map.get(child.path, 0),
                    )
                )
                for child in node.children:
                    sort_children(child)

        roots.sort(
            key=lambda node: (0 if node.is_dir else 1, order_map.get(node.path, 0))
        )
        for node in roots:
            sort_children(node)

        return roots

    def save_uploaded_file(
        self, file: UploadFile, directory: Optional[str] = None
    ) -> str:
        """
        Saves an uploaded file to the specified directory.

        Args:
            file: The uploaded file.
            directory: The directory where the file should be saved.

        Raises:
            InvalidFileName: If the filename is invalid.

        Returns:
            The path of the saved file.
        """
        filename = file.filename

        if not filename:
            raise InvalidFileName("Invalid filename.")

        _log.info("Saving uploaded %s to %s", filename, directory)

        file_path = resolve_absolute_path(filename, directory)

        with atomic_write(file_path, mode="wb") as buffer:
            buffer.write(file.file.read())
        return file_path


if __name__ == "__main__":
    manager = FileManager()

    print(manager.get_files_flat(root_dir="~/Music"))
