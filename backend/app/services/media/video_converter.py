import asyncio
import os
import subprocess
from os import PathLike
from pathlib import Path
from typing import Optional, Union

from app.core.logger import Logger
from app.util.file_util import file_name_parent_directory

_log = Logger(name=__name__)


class VideoConverter:
    """
    Service to get video details: duration and preview image.
    """

    ALLOWED_VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov")

    @staticmethod
    def is_video_file(file_path: str) -> bool:
        """
        Check if the file has one of the allowed video extensions.
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in VideoConverter.ALLOWED_VIDEO_EXTENSIONS

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
        command = VideoConverter.ffmpeg_command(input_file, temp_file)
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
            temp_file.replace(output_file)
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
            command = VideoConverter.ffmpeg_command(input_file, temp_file)
            debug = os.getenv("PX_LOG_LEVEL", "INFO").upper() == "DEBUG"

            command = VideoConverter.ffmpeg_command(input_file, temp_file)

            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE if not debug else subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )

            if not isinstance(output_file, Path):
                output_file = Path(output_file)

            temp_file.replace(output_file)

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

    @classmethod
    def convert_to_mp4(cls, video_file: str, output_file: str) -> Optional[str]:
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

        if os.path.exists(output_file) and os.path.getmtime(
            output_file
        ) >= os.path.getmtime(video_file):
            _log.debug(
                "Converted file already exists and is up to date: '%s'", output_file
            )
            return output_file

        return cls.convert_video(video_file, output_file)

    @staticmethod
    def video_duration(video_file: str) -> Optional[float]:
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

    @staticmethod
    def generate_video_poster(video_file: str, output_path: str) -> Optional[str]:
        """
        Generates a preview image (thumbnail) for the given video file.
        The preview filename incorporates the file modification time so that it
        gets refreshed if the video file changes.
        """
        parent_path = file_name_parent_directory(output_path)

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
            output_path,
        ]
        try:
            subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )
            return output_path if os.path.exists(output_path) else None

        except Exception as err:
            _log.error("Failed to generate preview for '%s': %s", video_file, err)
            return None
