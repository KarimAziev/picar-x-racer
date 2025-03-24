from __future__ import annotations

import os
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from app.core.logger import Logger
from app.exceptions.file_exceptions import InvalidFileName
from app.managers.file_management.file_cache import CacheEntry, CacheManager
from app.managers.file_management.file_manager import FileManager
from app.schemas.file_filter import (
    FileDetail,
    FileFilterModel,
    FileResponseModel,
    OrderingModel,
    SearchModel,
    ValueLabelOption,
)
from app.schemas.file_management import BatchFileResult
from app.services.file_management.file_filter_service import FileFilterService
from app.services.media.video_converter import VideoConverter
from app.util.atomic_write import atomic_write
from app.util.file_util import (
    file_name_parent_directory,
    file_to_relative,
    resolve_absolute_path,
)
from fastapi import UploadFile
from pydub import AudioSegment

_log = Logger(name=__name__)


@dataclass
class FileCachedMetadata:
    preview: Optional[str]
    duration: Optional[float]
    removable: Optional[bool] = True
    order: Optional[int] = None


class FileManagerService:
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

    def __init__(
        self,
        root_directory: str,
        cache_dir: str,
        file_manager: FileManager,
        filter_service: FileFilterService,
    ) -> None:
        self.root_directory: str = root_directory
        self._cache_dir: str = cache_dir
        self._cache_file: str = os.path.join(self._cache_dir, "metadata.json")
        self._preview_dir: str = os.path.join(self._cache_dir, "preview")
        self.filter_service = filter_service
        self.file_manager = file_manager
        self.cache_manager: CacheManager[FileCachedMetadata] = CacheManager(
            self._cache_file,
            lambda data: FileCachedMetadata(
                preview=data.get("preview"),
                duration=data.get("duration"),
                removable=data.get("removable"),
                order=data.get("order"),
            ),
        )

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

    def rename_file(self, relative_name: str, new_name: str) -> None:
        files_cache = self.cache_manager.get_cache()

        full_name = resolve_absolute_path(relative_name, self.root_directory)
        new_full_name = resolve_absolute_path(new_name, self.root_directory)

        self.file_manager.rename_file(full_name, new_full_name)

        file_cached_detail = files_cache.get(relative_name)

        if file_cached_detail:
            file_cached_detail.modified_time = os.path.getmtime(full_name)
            files_cache[new_name] = file_cached_detail
            del files_cache[relative_name]
            self.cache_manager.save_cache()

    def remove_file(self, relative_name: str) -> bool:
        full_name = resolve_absolute_path(relative_name, self.root_directory)
        files_cache = self.cache_manager.get_cache()
        file_cached_detail = files_cache.get(relative_name)

        if file_cached_detail:
            del files_cache[relative_name]
            self.cache_manager.save_cache()

        return self.file_manager.remove_file(full_name)

    def batch_remove_files(
        self, filenames: List[str]
    ) -> Tuple[List[BatchFileResult], List[Dict[str, str]]]:
        filenames = [
            resolve_absolute_path(file, self.root_directory) for file in filenames
        ]

        dirs = [item for item in filenames if os.path.isdir(item)]
        dirs_relative = [file_to_relative(d, self.root_directory) for d in dirs]

        responses, success_responses = self.file_manager.batch_remove_files(filenames)
        files_cache = self.cache_manager.get_cache()

        for key in list(files_cache):
            if any(key == d or key.startswith(d + os.sep) for d in dirs_relative):
                del files_cache[key]
                self.cache_manager.mark_dirty()

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
        dirs = [item for item in filenames if os.path.isdir(item)]
        dirs_relative = [file_to_relative(d, self.root_directory) for d in dirs]
        files_cache = self.cache_manager.get_cache()

        responses, success_responses = self.file_manager.batch_move_files(
            filenames, target_dir=target_dir
        )

        for key in list(files_cache):
            if any(key == d or key.startswith(d + os.sep) for d in dirs_relative):
                del files_cache[key]
                self.cache_manager.mark_dirty()

        self.cache_manager.maybe_save()

        return responses, success_responses

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

        result = self.file_manager.get_files_tree(
            root_dir=self.root_directory,
            subdir=subdir,
            filter_model=filter_model,
            search=search,
            ordering=ordering,
            filtered_file_transformer=self._add_duration,
        )
        self.cache_manager.maybe_save()

        return result

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
                    preview = self.get_video_poster(full_name)
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

        return preview_path

    def get_video_poster(self, video_file: str) -> Optional[str]:
        """
        Generates a preview image (thumbnail) for the given video file.
        The preview filename incorporates the file modification time so that it
        gets refreshed if the video file changes.
        """
        video_file = resolve_absolute_path(video_file, self.root_directory)
        preview_path = self._preview_image_path(video_file)

        if os.path.exists(preview_path):
            return preview_path

        _log.info("Generating video poster for '%s': '%s'", video_file, preview_path)

        return VideoConverter.generate_video_poster(video_file, preview_path)

    def convert_video_for_streaming(self, video_file: str) -> Optional[str]:
        video_file = resolve_absolute_path(video_file, self.root_directory)
        mp4_ext = ".mp4"

        if video_file.endswith(mp4_ext):
            return video_file

        basename = Path(
            file_to_relative(
                video_file,
                self.root_directory,
            )
        ).with_suffix(mp4_ext)

        output_file = Path(os.path.join(self._preview_dir, basename))
        output_file_posix = output_file.as_posix()

        if output_file.exists() and os.path.getmtime(output_file) >= os.path.getmtime(
            video_file
        ):
            _log.debug(
                "Converted file already exists and is up to date: '%s'", output_file
            )
            return output_file_posix

        _log.info(
            "Converting video %s for video streaming to %s",
            video_file,
            output_file_posix,
        )

        return VideoConverter.convert_to_mp4(video_file, output_file_posix)
