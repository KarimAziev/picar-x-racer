import json
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Protocol, cast

import cv2
import numpy as np
from app.core.logger import Logger
from app.core.video_capture_abc import VideoCaptureABC

if TYPE_CHECKING:
    from app.adapters.picamera_capture_adapter import PicameraCaptureAdapter
    from app.services.file_management.file_manager_service import FileManagerService

logger = Logger(__name__)


class _RecorderBackend(Protocol):
    def start(self) -> None: ...

    def write(self, frame: np.ndarray) -> None: ...

    def stop(self) -> None: ...


class _OpenCVRecorder:
    def __init__(self, path: str, width: int, height: int, fps: float) -> None:
        self.path = path
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps)
        self.writer: Optional[cv2.VideoWriter] = None

    def _guess_fourcc(self) -> str:
        suffix = Path(self.path).suffix.lower()
        container_map = {
            ".mp4": "mp4v",
            ".mov": "mp4v",
            ".avi": "XVID",
            ".mkv": "X264",
        }
        return container_map.get(suffix, "mp4v")

    def start(self) -> None:
        fourcc_name = self._guess_fourcc()
        fourcc = cv2.VideoWriter.fourcc(*fourcc_name)
        logger.info(
            "Recording video with OpenCV backend at %s (fourcc=%s), %sx%s, %.2f fps",
            self.path,
            fourcc_name,
            self.width,
            self.height,
            self.fps,
        )
        self.writer = cv2.VideoWriter(
            self.path, fourcc, self.fps, (self.width, self.height)
        )
        if not self.writer.isOpened():
            raise RuntimeError(
                f"Failed to initialise OpenCV video writer for '{self.path}'"
            )

    def write(self, frame: np.ndarray) -> None:
        if self.writer is not None:
            self.writer.write(frame)

    def stop(self) -> None:
        if self.writer is not None:
            self.writer.release()
            self.writer = None


class _PicameraRecorder:
    def __init__(
        self,
        adapter: "PicameraCaptureAdapter",
        path: str,
        width: int,
        height: int,
        fps: float,
    ) -> None:
        self.adapter = adapter
        self.path = path
        self.width = width
        self.height = height
        self.fps = fps
        self.encoder = None
        self.output = None
        self._active = False

    def _estimate_bitrate(self) -> int:
        if self.width > 0 and self.height > 0:
            fps = self.fps if self.fps and self.fps > 0 else 30.0
            target = int(self.width * self.height * fps * 0.07)
            return max(5_000_000, min(30_000_000, target))
        return 10_000_000

    def start(self) -> None:
        from picamera2.encoders import H264Encoder
        from picamera2.outputs import FfmpegOutput

        bitrate = self._estimate_bitrate()
        logger.info(
            "Recording video with Picamera2 backend at %s (bitrate=%s)",
            self.path,
            bitrate,
        )
        self.encoder = H264Encoder(bitrate=bitrate)
        self.output = FfmpegOutput(self.path)
        self.adapter.picam2.start_encoder(self.encoder, self.output)
        self._active = True

    def write(self, frame: np.ndarray) -> None:
        # Frames are pushed to the encoder by Picamera2 internally.
        pass

    def stop(self) -> None:
        if not self._active:
            return
        try:
            stop_encoder = getattr(self.adapter.picam2, "stop_encoder", None)
            if callable(stop_encoder):
                stop_encoder()
            else:
                self.adapter.picam2.stop_recording()
        finally:
            if self.output is not None:
                close_method = getattr(self.output, "close", None)
                if callable(close_method):
                    close_method()
            self.encoder = None
            self.output = None
            self._active = False


class VideoRecorderService:
    """
    Handles starting, writing frames to, and stopping video recordings.

    The service selects an appropriate recording backend based on the
    active capture adapter (Picamera2 when available, otherwise OpenCV).
    """

    def __init__(self, file_manager: "FileManagerService") -> None:
        self.file_manager = file_manager
        self.video_file_service = self.file_manager
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.current_video_path: Optional[str] = None
        self._recorder: Optional[_RecorderBackend] = None
        self.last_recording_info: Optional[dict[str, Any]] = None

    def _build_output_path(self) -> str:
        video_dir_path = Path(self.video_file_service.root_directory)
        video_dir_path.mkdir(exist_ok=True, parents=True)
        file_name = f"recording_{time.strftime('%Y-%m-%d-%H-%M-%S')}.mp4"
        return video_dir_path.joinpath(file_name).as_posix()

    def _start_picamera_recorder(
        self,
        capture: VideoCaptureABC,
        path: str,
        width: int,
        height: int,
        fps: float,
    ) -> Optional[_PicameraRecorder]:
        try:
            from app.adapters.picamera_capture_adapter import PicameraCaptureAdapter
        except Exception:
            return None

        if not isinstance(capture, PicameraCaptureAdapter):
            return None

        try:
            recorder = _PicameraRecorder(
                adapter=cast("PicameraCaptureAdapter", capture),
                path=path,
                width=width,
                height=height,
                fps=fps,
            )
            recorder.start()
            return recorder
        except Exception:
            logger.error(
                "Failed to start Picamera2 recorder; falling back to OpenCV.",
                exc_info=True,
            )
            return None

    def _probe_media_file(self, path: Optional[str]) -> Optional[dict[str, Any]]:
        if not path:
            return None

        file_path = Path(path)
        if not file_path.exists():
            logger.warning(
                "Recorded file %s not found for ffprobe inspection", file_path
            )
            return None

        entries = (
            "format=format_name,format_long_name,duration,bit_rate,size"
            ":stream=index,codec_type,codec_name,codec_long_name,profile,"
            "avg_frame_rate,pix_fmt,width,height,sample_rate,channels"
        )
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_entries",
            entries,
            str(file_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError:
            logger.warning(
                "ffprobe is not available on the system; skipping media inspection."
            )
            return None
        except subprocess.CalledProcessError as exc:
            error_output = (
                exc.stderr.strip() if isinstance(exc.stderr, str) else str(exc)
            )
            logger.error("ffprobe failed for %s: %s", file_path, error_output)
            return None

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.error("Failed to decode ffprobe output for %s", file_path)
            return None

    def _log_probe_results(self, info: dict[str, Any]) -> None:
        format_info = info.get("format") or {}
        format_name = format_info.get("format_name")
        format_long = format_info.get("format_long_name")
        duration = format_info.get("duration")
        bit_rate = format_info.get("bit_rate")
        size = format_info.get("size")

        logger.info(
            "Recorded media summary: format=%s (%s), duration=%ss, size=%s bytes, bit_rate=%s",
            format_name,
            format_long,
            duration,
            size,
            bit_rate,
        )

        streams = info.get("streams") or []
        for stream in streams:
            codec_type = stream.get("codec_type")
            idx = stream.get("index")
            codec_name = stream.get("codec_name")
            codec_long = stream.get("codec_long_name")
            profile = stream.get("profile")

            if codec_type == "video":
                width = stream.get("width")
                height = stream.get("height")
                pix_fmt = stream.get("pix_fmt")
                fps = self._format_frame_rate(stream.get("avg_frame_rate"))
                logger.info(
                    "Video stream #%s: codec=%s (%s), profile=%s, resolution=%sx%s, pix_fmt=%s, avg_fps=%s",
                    idx,
                    codec_name,
                    codec_long,
                    profile,
                    width,
                    height,
                    pix_fmt,
                    fps,
                )
            elif codec_type == "audio":
                sample_rate = stream.get("sample_rate")
                channels = stream.get("channels")
                logger.info(
                    "Audio stream #%s: codec=%s (%s), profile=%s, sample_rate=%s, channels=%s",
                    idx,
                    codec_name,
                    codec_long,
                    profile,
                    sample_rate,
                    channels,
                )

    @staticmethod
    def _format_frame_rate(value: Optional[str]) -> Optional[str]:
        if not value or value in {"0/0", "0/1"}:
            return None
        try:
            numerator, denominator = value.split("/")
            num = float(numerator)
            den = float(denominator)
            if den == 0:
                return value
            return f"{num / den:.2f} fps"
        except Exception:
            return value

    def start_recording(
        self, capture: VideoCaptureABC, width: int, height: int, fps: float
    ) -> None:
        """
        Starts a new video recording session using the best available backend.

        Args:
            capture: The active capture adapter producing frames.
            width: Frame width.
            height: Frame height.
            fps: Frames per second for the recording pipeline.
        """
        output_path = self._build_output_path()
        self.last_recording_info = None

        recorder: Optional[_RecorderBackend] = self._start_picamera_recorder(
            capture=capture, path=output_path, width=width, height=height, fps=fps
        )

        if recorder is None:
            opencv_recorder = _OpenCVRecorder(
                path=output_path, width=width, height=height, fps=fps
            )
            opencv_recorder.start()
            recorder = opencv_recorder
            self.video_writer = opencv_recorder.writer
        else:
            self.video_writer = None

        self._recorder = recorder
        self.current_video_path = output_path

    def write_frame(self, frame: np.ndarray) -> None:
        if self._recorder is None:
            return
        try:
            self._recorder.write(frame)
        except Exception:
            logger.error("Error writing frame to recorder", exc_info=True)

    def stop_recording_safe(self) -> None:
        try:
            self.stop_recording()
        except Exception:
            logger.error("Error releasing video recorder", exc_info=True)

    def stop_recording(self) -> None:
        if self._recorder is None:
            return

        logger.info("Releasing video recorder")
        self._recorder.stop()

        probe_info = self._probe_media_file(self.current_video_path)
        if probe_info is not None:
            self.last_recording_info = probe_info
            self._log_probe_results(probe_info)
        else:
            self.last_recording_info = None

        self._recorder = None
        self.video_writer = None

    def get_last_recording_info(self) -> Optional[dict[str, Any]]:
        """Return the cached ffprobe metadata for the most recent recording."""

        return self.last_recording_info
