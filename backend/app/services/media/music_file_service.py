import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.core.logger import Logger
from app.exceptions.file_exceptions import DefaultFileRemoveAttempt
from app.exceptions.music import ActiveMusicTrackRemovalError
from app.managers.file_management.file_cache import CacheEntry
from app.schemas.file_filter import (
    FileDetail,
    FileFilterModel,
    FileResponseModel,
    FilterInfo,
    OrderingModel,
    SearchModel,
)
from app.schemas.file_management import BatchFileResult
from app.services.file_management.file_manager_service import (
    FileCachedMetadata,
    FileManagerService,
)
from app.services.media.music_service import MusicService
from app.util.file_util import abbreviate_path
from app.util.list_util import take_while

_log = Logger(__name__)


class MusicFileService(FileManagerService):
    def __init__(
        self, music_service: MusicService, default_music_dir: str, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.music_service = music_service
        self.default_music_dir = default_music_dir
        default_files: List[str] = []
        for file in os.listdir(self.default_music_dir):
            file_path = os.path.join(self.default_music_dir, file)
            if os.path.isfile(file_path):
                default_files.append(file_path)

        if not os.path.exists(self.root_directory):
            failed = False
            try:
                Path(self.root_directory).mkdir(parents=True)
            except Exception as e:
                failed = True
                _log.error("Failed to create music directory: %s", e)

            if not failed:
                for file in default_files:
                    shutil.copy(
                        file, os.path.join(self.root_directory, os.path.basename(file))
                    )

    def batch_remove_files(
        self, filenames: List[str]
    ) -> Tuple[List[BatchFileResult], List[Dict[str, str]]]:
        rejected_filenames: List[BatchFileResult] = []
        filtered_filenames: List[str] = []
        abs_filenames = [os.path.join(self.root_directory, item) for item in filenames]

        if (
            self._is_playing_dir_or_file(abs_filenames)
            or self.music_service.track in filenames
        ):
            self.music_service.next_track()

        if self.music_service.is_playing and (
            self._is_playing_dir_or_file(abs_filenames)
            or self.music_service.track in filenames
        ):
            raise ActiveMusicTrackRemovalError("Can't remove active music track")

        for relative_name in filenames:
            if self._is_default_file(relative_name):
                rejected_filenames.append(
                    BatchFileResult(
                        filename=relative_name,
                        success=False,
                        error="Cannot remove the default file.",
                    )
                )
            else:
                filtered_filenames.append(relative_name)

        return super().batch_remove_files(filenames=filtered_filenames)

    def list_sorted_tracks(self) -> List[FileDetail]:
        files_cache = self.cache_manager.get_cache()
        all_files = self.file_manager.list_files_recursively(self.root_directory)
        max_len = len(all_files)
        audio_files: List[FileDetail] = [
            self.add_metadata(item) for item in all_files if item.type == "audio"
        ]
        ordering: Dict[str, int] = {}
        for key, entry in files_cache.items():
            if isinstance(entry.details.order, int):
                ordering[key] = entry.details.order

        self.cache_manager.maybe_save()

        sorted_tracks: List[FileDetail] = sorted(
            audio_files, key=lambda file: ordering.get(file.path, max_len), reverse=True
        )

        return sorted_tracks

    def save_custom_music_order(self, filenames: List[str]):
        files_cache = self.cache_manager.get_cache()
        order_set: Set[str] = set()

        for i, key in enumerate(filenames):
            order_set.add(key)
            if not key in files_cache:
                full_name = os.path.join(self.root_directory, key)
                is_default_file = False
                if not os.path.exists(full_name):
                    full_name = os.path.join(self.default_music_dir, key)
                    if not os.path.exists(full_name):
                        raise FileNotFoundError(f"File {key} not found")
                    else:
                        is_default_file = True

                modified_time = os.path.getmtime(full_name)
                duration = self._audio_duration(full_name)

                files_cache[key] = CacheEntry(
                    modified_time=modified_time,
                    details=FileCachedMetadata(
                        preview=None,
                        duration=duration,
                        order=i,
                        removable=not is_default_file,
                    ),
                )
                self.cache_manager.mark_dirty()

            else:
                entry = files_cache[key]
                if entry.details.order != i:
                    entry.details.order = i
                    self.cache_manager.mark_dirty()

        for key, entry in files_cache.items():
            if not key in order_set and isinstance(entry.details.order, int):
                del entry.details.order
                self.cache_manager.mark_dirty()

        sorted_tracks = self.list_sorted_tracks()
        self.music_service.update_tracks(sorted_tracks)
        return sorted_tracks

    def remove_file(self, relative_name: str) -> bool:
        if self.music_service.track == relative_name:
            self.music_service.next_track()
        if self.music_service.track == relative_name and self.music_service.is_playing:
            raise ActiveMusicTrackRemovalError("Can't remove the playing track.")

        file_abs = os.path.join(self.root_directory, relative_name)
        file_abs_default = os.path.join(self.default_music_dir, relative_name)

        if not os.path.exists(file_abs):
            if os.path.exists(file_abs_default):
                raise DefaultFileRemoveAttempt("Cannot remove the default file.")
            else:
                raise FileNotFoundError("File not found.")

        status = super().remove_file(relative_name)
        if status:
            sorted_tracks = self.list_sorted_tracks()
            self.music_service.update_tracks(sorted_tracks)

        return status

    def _is_playing_dir_or_file(self, abs_filenames: List[str]) -> bool:
        active_track_full = (
            os.path.join(self.root_directory, self.music_service.track)
            if self.music_service.track
            else None
        )

        active_track_dirs = (
            take_while(
                Path(active_track_full).parents, lambda x: x != self.root_directory
            )
            if active_track_full and os.path.exists(active_track_full)
            else None
        )

        if not active_track_dirs:
            return False

        return any(file in active_track_dirs for file in abs_filenames)

    def _is_default_file(self, relative_name: str) -> bool:
        file_abs = os.path.join(self.root_directory, relative_name)
        file_abs_default = os.path.join(self.default_music_dir, relative_name)

        if not os.path.exists(file_abs) and os.path.exists(file_abs_default):
            return True
        else:
            return False

    def add_metadata(self, file_model: FileDetail) -> FileDetail:

        file_model = self._add_duration(file_model)
        files_cache = self.cache_manager.get_cache()
        file_cache = files_cache.get(file_model.path)
        if file_cache and isinstance(file_cache.details.order, int):
            file_model.order = file_cache.details.order
        return file_model

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

        all_files = self.file_manager.list_files_recursively(
            self.root_directory, subdir
        )

        filtered_files = self.file_manager.sort_files(
            self.file_manager.filter_service.filter_files(
                all_files,
                filter_model=filter_model,
                search=search,
                filtered_file_transformer=self.add_metadata,
            ),
            ordering,
        )
        grouped_files = self.file_manager.group_files(filtered_files)

        filter_info = FilterInfo(type=self.file_manager.file_types)

        self.cache_manager.maybe_save()
        return FileResponseModel(
            data=grouped_files,
            filter_info=filter_info,
            dir=subdir,
            root_dir=abbreviate_path(self.root_directory),
        )
