from __future__ import annotations

import datetime
import os
import zoneinfo
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.logger import Logger
from app.exceptions.file_exceptions import InvalidFileName
from app.managers.file_cache import CacheEntry, CacheManager
from app.schemas.file_filter import (
    FileDetail,
    FileFilterModel,
    FileResponseModel,
    FilterInfo,
    FilterMatchMode,
    GroupedFile,
    OrderingModel,
    SearchModel,
    SortDirection,
    ValueLabelOption,
)
from app.schemas.file_management import BatchFileResult
from app.services.video_converter import VideoConverter
from app.util.atomic_write import atomic_write
from app.util.file_util import (
    abbreviate_path,
    exclude_nested_files,
    file_name_parent_directory,
    file_to_relative,
    guess_mime_type,
    resolve_absolute_path,
)
from fastapi import UploadFile
from pydub import AudioSegment
from rapidfuzz import fuzz

_log = Logger(name=__name__)


@dataclass
class FileCachedMetadata:
    preview: Optional[str]
    duration: Optional[float]


def file_cached_metadata_factory(data: Dict[str, Any]) -> FileCachedMetadata:
    return FileCachedMetadata(
        preview=data.get("preview"),
        duration=data.get("duration"),
    )


class FileManagerService:
    @classmethod
    def is_video(cls, file_detail: FileDetail):
        return file_detail.type == "video" and not cls.is_archive(file_detail)

    @classmethod
    def is_audio(cls, file_detail: FileDetail):
        return file_detail.type == "audio" and not cls.is_archive(file_detail)

    @classmethod
    def is_archive(cls, file_detail: FileDetail):
        return file_detail.name.endswith(
            (".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".rar")
        )

    file_types: List[ValueLabelOption] = [
        ValueLabelOption(value=item, label=item.title())
        for item in [
            "application",
            "audio",
            "font",
            "example",
            "image",
            "message",
            "model",
            "multipart",
            "text",
            "video",
        ]
    ]

    def __init__(self, root_directory: str, cache_dir: str) -> None:
        self.root_directory: str = root_directory
        self._cache_dir: str = cache_dir
        self._cache_file: str = os.path.join(self._cache_dir, "metadata.json")
        self._preview_dir: str = os.path.join(self._cache_dir, "preview")
        self.cache_manager: CacheManager[FileCachedMetadata] = CacheManager(
            self._cache_file, file_cached_metadata_factory
        )

    def _audio_duration(self, filename: str) -> float:
        audio: AudioSegment = AudioSegment.from_file(filename)
        return len(audio) / 1000.0

    def _duration(self, file_model: FileDetail) -> Optional[float]:
        duration_fn = (
            VideoConverter.video_duration
            if self.is_video(file_model)
            else self._audio_duration if self.is_audio(file_model) else None
        )
        if duration_fn is None:
            return None

        cache: Dict[str, CacheEntry[FileCachedMetadata]] = (
            self.cache_manager.get_cache()
        )
        full_name: str = os.path.join(self.root_directory, file_model.path)
        mod_time: float = os.path.getmtime(full_name)
        relative_name: str = file_model.path
        file_cache: Optional[CacheEntry[FileCachedMetadata]] = cache.get(relative_name)

        if file_cache is None or file_cache.modified_time != mod_time:
            duration: Optional[float] = None
            preview: Optional[str] = None
            try:
                duration = duration_fn(full_name)
            except Exception as e:
                _log.error("Error measuring duration for %s: %s", full_name, e)

            if self.is_video(file_model):
                try:
                    preview = self.video_preview(full_name)
                except Exception as e:
                    _log.error("Error creating preview for %s: %s", full_name, e)

            cache[relative_name] = CacheEntry(
                modified_time=mod_time,
                details=FileCachedMetadata(preview=preview, duration=duration),
            )
            self.cache_manager.mark_dirty()
            return duration
        else:
            return file_cache.details.duration

    def _add_duration(self, file_model: FileDetail) -> FileDetail:
        file_model.duration = self._duration(file_model)
        return file_model

    def _preview_image_path(self, video_file: Union[str, PathLike[str]]):
        basename = str(
            Path(
                file_to_relative(
                    Path(video_file).as_posix(),
                    self.root_directory,
                )
            ).with_suffix("")
        )

        video_mod_time = os.path.getmtime(video_file)
        preview_filename = f"{basename}_{int(video_mod_time)}.jpg"
        preview_path = os.path.join(self._preview_dir, preview_filename)
        _log.info(
            "video '%s' -> basename='%s', root_directory='%s', preview_path='%s'",
            video_file,
            basename,
            self.root_directory,
            preview_path,
        )
        return preview_path

    def video_preview(self, video_file: str) -> Optional[str]:
        """
        Generates a preview image (thumbnail) for the given video file.
        The preview filename incorporates the file modification time so that it
        gets refreshed if the video file changes.
        """
        video_file = resolve_absolute_path(video_file, self.root_directory)
        preview_path = self._preview_image_path(video_file)

        if os.path.exists(preview_path):
            return preview_path

        return VideoConverter.generate_video_preview(video_file, preview_path)

    def video_stream(self, video_file: str) -> Optional[str]:
        video_file = resolve_absolute_path(video_file, self.root_directory)
        if video_file.endswith(".mp4"):
            return video_file

        basename = Path(
            file_to_relative(
                video_file,
                self.root_directory,
            )
        ).with_suffix(".mp4")

        output_file = Path(os.path.join(self._preview_dir, basename))

        if output_file.exists() and os.path.getmtime(output_file) >= os.path.getmtime(
            video_file
        ):
            _log.debug(
                "Converted file already exists and is up to date: '%s'", output_file
            )
            return output_file.as_posix()

        return VideoConverter.convert_to_mp4(video_file, output_file.as_posix())

    def rename_file(self, relative_name: str, new_name: str):
        files_cache = self.cache_manager.get_cache()

        full_name = os.path.join(self.root_directory, relative_name)
        new_full_name = os.path.join(self.root_directory, new_name)
        parent_dir = Path(file_name_parent_directory(new_name))

        parent_dir.mkdir(parents=True, exist_ok=True)
        Path(full_name).replace(new_full_name)

        file_cached_detail = files_cache.get(relative_name)

        if file_cached_detail:
            file_cached_detail.modified_time = os.path.getmtime(full_name)
            files_cache[new_name] = file_cached_detail
            del files_cache[relative_name]
            self.cache_manager.save_cache()

    def remove_file(self, relative_name: str):
        full_name = resolve_absolute_path(relative_name, self.root_directory)
        file_path = Path(full_name)
        files_cache = self.cache_manager.get_cache()
        file_cached_detail = files_cache.get(relative_name)

        if file_cached_detail:
            del files_cache[relative_name]
            self.cache_manager.save_cache()

        if not file_path.exists():
            return False
        elif file_path.is_dir():
            file_path.rmdir()
            return True
        else:
            file_path.unlink()
            return True

    def batch_remove_files(
        self, filenames: List[str]
    ) -> Tuple[List[BatchFileResult], List[Dict[str, str]]]:
        filenames = [
            resolve_absolute_path(file, self.root_directory) for file in filenames
        ]
        relative_filenames = [
            file_to_relative(file, self.root_directory) for file in filenames
        ]
        filtered_files = exclude_nested_files(filenames)
        responses: List[BatchFileResult] = []
        success_responses: List[Dict[str, str]] = []
        files_cache = self.cache_manager.get_cache()

        for file_path in filtered_files:
            filename = file_path.as_posix()
            relative_name = file_to_relative(filename, self.root_directory)
            _log.info("Removing file '%s'", filename)
            result = False
            error: Optional[str] = None
            try:
                file_path.rmdir() if file_path.is_dir() else file_path.unlink()
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

        for relative_name in relative_filenames:
            file_cached_detail = files_cache.get(relative_name)
            if file_cached_detail:
                del files_cache[relative_name]
                self._should_write_cache = True

        self.cache_manager.maybe_save()

        return responses, success_responses

    def batch_move_files(
        self, filenames: List[str], target_dir: str
    ) -> Tuple[List[BatchFileResult], List[Dict[str, str]]]:
        target_dir = resolve_absolute_path(target_dir, self.root_directory)

        if not os.path.isdir(target_dir) and os.path.exists(target_dir):
            target_dir = file_name_parent_directory(target_dir).as_posix()

        filenames = [
            resolve_absolute_path(file, self.root_directory) for file in filenames
        ]
        relative_filenames = [
            file_to_relative(file, self.root_directory) for file in filenames
        ]
        filtered_files = exclude_nested_files(filenames)
        responses: List[BatchFileResult] = []
        success_responses: List[Dict[str, str]] = []
        files_cache = self.cache_manager.get_cache()
        target_dir_path = Path(os.path.join(self.root_directory, target_dir))
        target_dir_path.parent.mkdir(exist_ok=True, parents=True)

        for file_path in filtered_files:
            filename = file_path.as_posix()
            relative_name = file_to_relative(filename, self.root_directory)
            new_name = os.path.join(target_dir, os.path.basename(relative_name))
            _log.info(
                "Moving file '%s' to '%s' as '%s'", filename, target_dir, new_name
            )
            result = False
            error: Optional[str] = None
            try:
                file_path.rename(new_name)
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

        for relative_name in relative_filenames:
            file_cached_detail = files_cache.get(relative_name)
            if file_cached_detail:
                del files_cache[relative_name]
                self._should_write_cache = True

        self.cache_manager.maybe_save()

        return responses, success_responses

    def _file_to_relative(self, file: str) -> str:
        if file.startswith("~"):
            file = os.path.expanduser(file)
        if os.path.isabs(file):
            return file_to_relative(file, self.root_directory)
        return file

    def _file_to_model(self, full_path: str) -> FileDetail:
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

        relative_path = file_to_relative(full_path, self.root_directory)
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

    def list_files(self, subdir: Optional[str] = None) -> List[FileDetail]:
        """
        Walk the directory tree and apply searching and filtering.
        """
        files: List[FileDetail] = []

        dir = (
            os.path.join(self.root_directory, subdir)
            if subdir is not None
            else self.root_directory
        )

        for dirpath, dirnames, filenames in os.walk(dir):
            relative_dir = os.path.relpath(dirpath, dir)
            if relative_dir == ".":
                relative_dir = ""

            for name in dirnames + filenames:
                full_path = os.path.join(dirpath, name)
                detail = self._file_to_model(full_path)
                files.append(detail)

        return files

    def _filter_files(
        self,
        files: list[FileDetail],
        filter_model: Optional[FileFilterModel] = None,
        search: Optional[SearchModel] = None,
    ) -> List[FileDetail]:
        """
        Walk the directory tree and apply searching and filtering.
        """
        predicates = []

        if search and search.value:
            search_field = search.field or "name"
            search_val = search.value.lower()

            def fuzzy_predicate(f: FileDetail) -> bool:
                value = getattr(f, search_field, "").lower()
                score = fuzz.WRatio(search_val, value)
                return score >= 70

            predicates.append(fuzzy_predicate)

        if filter_model and filter_model.modified:
            start_date, end_date = filter_model.modified.date_range()

            def mod_predicate(f: FileDetail) -> bool:
                if f.modified is None:
                    return False
                mod_dt = datetime.datetime.fromtimestamp(
                    f.modified, tz=zoneinfo.ZoneInfo("UTC")
                ).replace(tzinfo=None)
                if start_date and mod_dt < start_date:
                    return False
                if end_date and mod_dt > end_date:
                    return False
                return True

            predicates.append(mod_predicate)

        if filter_model and filter_model.type and filter_model.type.value:
            filter_type = filter_model.type
            filter_value = filter_model.type.value
            filter_vals = {v.lower() for v in filter_value}

            def type_predicate(f: FileDetail) -> bool:
                if not f.type:
                    return False
                t = f.type.lower()
                if filter_type.match_mode == FilterMatchMode.IN:
                    return t in filter_vals
                elif filter_type.match_mode == FilterMatchMode.EQUALS:
                    return t == list(filter_vals)[0]
                elif filter_type.match_mode == FilterMatchMode.CONTAINS:
                    return any(val in t for val in filter_vals)
                return True

            predicates.append(type_predicate)

        if (
            filter_model
            and filter_model.content_type
            and filter_model.content_type.value
        ):
            filter_type = filter_model.content_type
            filter_value = filter_model.content_type.value
            filter_vals = {v.lower() for v in filter_value}

            def content_type_predicate(f: FileDetail) -> bool:
                if not f.content_type:
                    return False
                ct = f.content_type.lower()
                if filter_type.match_mode == FilterMatchMode.IN:
                    return ct in filter_vals
                elif filter_type.match_mode == FilterMatchMode.EQUALS:
                    return ct == list(filter_vals)[0]
                elif filter_type.match_mode == FilterMatchMode.CONTAINS:
                    return any(val in ct for val in filter_vals)
                return True

            predicates.append(content_type_predicate)

        if (
            filter_model
            and filter_model.file_suffixes
            and filter_model.file_suffixes.value
        ):
            suffixes = tuple(v.lower() for v in filter_model.file_suffixes.value)

            def suffix_predicate(f: FileDetail) -> bool:
                return f.name.lower().endswith(suffixes)

            predicates.append(suffix_predicate)

        filtered_files = [
            self._add_duration(f) for f in files if all(pred(f) for pred in predicates)
        ]

        self.cache_manager.maybe_save()

        return filtered_files

    def sort_files(
        self, files: List[FileDetail], ordering: Optional[OrderingModel] = None
    ):
        if ordering and ordering.field:
            field = ordering.field
            reverse = ordering.direction == SortDirection.desc
            try:
                files.sort(key=lambda x: getattr(x, field) or 0, reverse=reverse)
            except AttributeError:
                pass

        return files

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
        all_files = self.list_files(subdir)
        filtered_files = self.sort_files(
            self._filter_files(all_files, filter_model, search), ordering
        )

        self.cache_manager.maybe_save()

        grouped_files = self.group_files(filtered_files)

        filter_info = FilterInfo(type=self.file_types)

        return FileResponseModel(
            data=grouped_files,
            filter_info=filter_info,
            dir=subdir,
            root_dir=abbreviate_path(self.root_directory),
        )

    def group_files(self, files: List[FileDetail]) -> List[GroupedFile]:
        """
        Group files and directories into a hierarchical tree.
        Directories are always placed before files within each folder.
        To preserve the pre-sorted order from get_files, we first capture an order index.
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
            str: The path of the saved file.
        """
        directory = (
            resolve_absolute_path(directory, self.root_directory)
            if directory
            else self.root_directory
        )
        filename = file.filename
        if not filename:
            raise InvalidFileName("Invalid filename.")

        file_path = resolve_absolute_path(filename, directory)

        with atomic_write(file_path, mode="wb") as buffer:
            buffer.write(file.file.read())
        return file_path
