import asyncio
import json
import os
import subprocess
from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

from app.core.logger import Logger
from app.util.atomic_write import atomic_write
from app.util.file_util import file_name_parent_directory, file_to_relative


class FileDetails(TypedDict):
    track: str
    preview: Optional[str]
    duration: Optional[float]
    error: Optional[str]


class CacheDict(TypedDict):
    modified_time: float
    details: FileDetails


_log = Logger(name=__name__)


class VideoService:
    """
    Service to get video details: duration and preview image.
    """

    ALLOWED_VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov")

    def __init__(
        self, video_dir: str, video_cache_path: str, preview_cache_dir: str
    ) -> None:
        self.video_dir = video_dir
        self.video_cache_path = video_cache_path
        self.preview_cache_dir = preview_cache_dir
        self._cache: Dict[str, CacheDict] = self._load_cache()

    @staticmethod
    def is_video_file(file_path: str) -> bool:
        """
        Check if the file has one of the allowed video extensions.
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in VideoService.ALLOWED_VIDEO_EXTENSIONS

    @staticmethod
    def ffmpeg_command(
        input_file: Union[str, PathLike[str]], output_file: Union[str, PathLike[str]]
    ):
        return [
            "ffmpeg",
            "-y",
            "-fflags",
            "+genpts",
            "-vsync",
            "vfr",
            "-i",
            str(input_file),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_file),
        ]

    @staticmethod
    async def convert_video_async(
        input_file: Union[str, PathLike[str]], output_file: Union[str, PathLike[str]]
    ) -> Optional[str]:
        temp_file = Path(input_file).with_suffix(".temp.mp4")
        command = VideoService.ffmpeg_command(input_file, temp_file)
        command.insert(0, "nice")
        command.insert(1, "-n")
        command.insert(2, "10")
        _log.info("starting command %s", command)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _log.info("starting ffmpeg subprocess %s", process)

        _, stderr = await process.communicate()

        if process.returncode != 0:
            _log.error(f"FFmpeg failed with error: {stderr.decode()}")
            return None

        try:
            output_file = Path(output_file)
            temp_file.rename(output_file)
            if output_file.exists():
                return output_file.as_posix()
        except Exception:
            _log.error("Failed to rename %s to %s", temp_file, output_file)

    @staticmethod
    def convert_video(
        input_file: Union[str, PathLike[str]], output_file: Union[str, PathLike[str]]
    ) -> Optional[str]:

        try:
            _log.info(
                "Converting input_file '%s', exists=%s",
                input_file,
                os.path.exists(input_file),
            )
            temp_file = Path(input_file).with_suffix(".temp.mp4")
            command = VideoService.ffmpeg_command(input_file, temp_file)
            debug = os.getenv("PX_LOG_LEVEL", "INFO").upper() == "DEBUG"

            command = VideoService.ffmpeg_command(input_file, temp_file)

            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE if not debug else subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )

            if not isinstance(output_file, Path):
                output_file = Path(output_file)

            temp_file.rename(output_file)

            if output_file.exists():
                _log.info(
                    "Successfully converted '%s' to '%s'", input_file, output_file
                )
                return output_file.as_posix()
            else:
                _log.error(
                    "Conversion completed but output file not found: '%s'", output_file
                )
                return None

        except subprocess.CalledProcessError as e:
            _log.error(f"FFmpeg processing failed: {e}")
        except FileNotFoundError as e:
            _log.error(f"FFmpeg converting failed: {e}")
        except Exception:
            _log.error("Unhandled error during FFmpeg converting", exc_info=True)

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.video_cache_path):
            try:
                with open(self.video_cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as err:
                _log.error("Error loading video cache: %s", err)
        return {}

    def _save_cache(self) -> None:
        try:
            with atomic_write(self.video_cache_path, mode="w") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as err:
            _log.error("Error saving video cache: %s", err)

    def expand_preview_image(self, image_filename: str) -> str:
        """Return full filename for image filename, relative to video preview cache directory."""
        return os.path.join(self.preview_cache_dir, image_filename)

    def convert_to_mp4(self, video_file: str) -> Optional[str]:
        """
        Converts the input video to MP4 format using FFmpeg.
        If the file is already MP4, it returns the original path.
        For avi, mkv, or mov inputs, a new MP4 file is generated.

        Args:
            video_file: The full path to the input video file.
            out_dir: The directory to save. If not provided, the same directory as for video file will be used.

        Returns:
            The path to the converted MP4 file, or None if conversion failed.
        """
        input_path = Path(video_file)
        ext = input_path.suffix.lower()

        if ext == ".mp4":
            _log.debug("File '%s' is already MP4.", video_file)
            return video_file

        basename = Path(
            file_to_relative(
                video_file,
                self.video_dir,
            )
        ).with_suffix(".mp4")

        output_file = Path(os.path.join(self.preview_cache_dir, basename))

        if output_file.exists() and os.path.getmtime(output_file) >= os.path.getmtime(
            video_file
        ):
            _log.debug(
                "Converted file already exists and is up to date: '%s'", output_file
            )
            return output_file.as_posix()

        return self.convert_video(video_file, output_file)

    def video_duration(self, video_file: str) -> Optional[float]:
        """
        Uses ffprobe to get the duration of the video.

        Requires ffmpeg to be installed, since ffprobe is part of the ffmpeg suite.
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_file,
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            duration_str = result.stdout.strip()
            return float(duration_str) if duration_str else None
        except Exception as err:
            _log.error("Failed to get duration for '%s': %s", video_file, err)
            return None

    def preview_image_path(self, video_file: Union[str, PathLike[str]]):
        basename = str(
            Path(
                file_to_relative(
                    Path(video_file).as_posix(),
                    self.video_dir,
                )
            ).with_suffix("")
        )

        _log.info("video '%s' -> basename='%s'", video_file, basename)

        video_mod_time = os.path.getmtime(video_file)
        preview_filename = f"{basename}_{int(video_mod_time)}.jpg"
        preview_path = os.path.join(self.preview_cache_dir, preview_filename)
        return preview_path

    def remove_video(self, relative_name: str):
        full_name = Path(os.path.join(self.video_dir, relative_name))
        preview_file_name = Path(self.preview_image_path(full_name))

        if full_name.exists():
            _log.info("Removing video file '%s'", full_name)
            full_name.unlink()

        if preview_file_name.exists():
            _log.info("Removing preview video image '%s'", preview_file_name)
            preview_file_name.unlink()

    def generate_video_preview(self, video_file: str) -> Optional[str]:
        """
        Generates a preview image (thumbnail) for the given video file.
        The preview filename incorporates the file modification time so that it
        gets refreshed if the video file changes.
        """
        preview_path = self.preview_image_path(video_file)

        if os.path.exists(preview_path):
            return preview_path

        parent_path = file_name_parent_directory(preview_path)

        try:
            parent_path.mkdir(exist_ok=True, parents=True)
        except Exception as err:
            _log.error("Error creating preview cache directory: %s", err)
            return None

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            video_file,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            preview_path,
        ]
        try:
            subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            return preview_path if os.path.exists(preview_path) else None

        except Exception as err:
            _log.error("Failed to generate preview for '%s': %s", video_file, err)
            return None

    def video_file_to_relative(self, file: str):
        if file.startswith("~"):
            file = os.path.expanduser(file)
        if os.path.isabs(file):
            return file_to_relative(file, self.video_dir)
        return file

    def get_video_details(self, video_file: str) -> Optional[FileDetails]:
        """
        Returns a dictionary of video details: track name, duration, preview image,
        and optionally error details if processing failed.

        The cache is used to avoid recalculating if the file’s modified time hasn’t changed.
        Now, both successful details and failure state (with an "error" field) are cached.
        """
        if not os.path.exists(video_file):
            _log.error("Video file not found: '%s'", video_file)
            return None

        relative_name = self.video_file_to_relative(video_file)

        mod_time = os.path.getmtime(video_file)
        cached = self._cache.get(relative_name)
        if cached and cached.get("modified_time") == mod_time:
            _log.debug("Using cached video details for '%s'", video_file)
            details = cached.get("details")
            return details if details.get("duration") else None

        _log.debug("Refreshing video details for '%s'", video_file)

        details: FileDetails = {
            "track": relative_name,
            "duration": None,
            "error": None,
            "preview": None,
        }
        duration = self.video_duration(video_file)
        if duration is None:
            error_msg = "Failed to extract video duration."
            details.update({"duration": None, "preview": None, "error": error_msg})
            _log.error("Error processing '%s': %s", video_file, error_msg)
            self._cache[relative_name] = {
                "modified_time": mod_time,
                "details": details,
            }
            self._save_cache()
            return None

        details["duration"] = duration
        preview = self.generate_video_preview(video_file)
        if preview is None:
            error_msg = "Failed to generate video preview."
            details["preview"] = None
            details["error"] = error_msg
            _log.error("Error processing '%s': %s", video_file, error_msg)
        else:
            details["preview"] = file_to_relative(preview, self.preview_cache_dir)

        self._cache[relative_name] = {"modified_time": mod_time, "details": details}
        self._save_cache()
        return details if details.get("duration") else None

    def list_videos_with_details(self) -> List[FileDetails]:
        """
        Recursively lists all video files in the video directory and returns their details.
        Only files with allowed video extensions (e.g. .mp4, .mkv, .avi, .mov) are processed.
        """
        if not os.path.exists(self.video_dir):
            return []

        result: List[FileDetails] = []
        for root, _, files in os.walk(self.video_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and self.is_video_file(file_path):
                    details = self.get_video_details(file_path)
                    if details is not None:
                        result.append(details)

        result.sort(
            key=lambda details: (
                os.path.getmtime(os.path.join(self.video_dir, details["track"]))
                if os.path.exists(os.path.join(self.video_dir, details["track"]))
                else 0
            ),
            reverse=True,
        )
        return result


if __name__ == "__main__":
    from app.config.config import settings as app_config

    user_videos_dir = app_config.PX_VIDEO_DIR
    video_cache_path = app_config.VIDEO_CACHE_FILE_PATH
    video_cache_preview_dir = app_config.VIDEO_CACHE_PREVIEW_DIR
    video_service = VideoService(
        video_cache_path=video_cache_path,
        preview_cache_dir=video_cache_preview_dir,
        video_dir=user_videos_dir,
    )
    videos = video_service.list_videos_with_details()
    print("video details", videos)
