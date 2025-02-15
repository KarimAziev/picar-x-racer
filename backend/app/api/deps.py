from functools import lru_cache

from app.adapters.video_device_adapter import VideoDeviceAdapter
from app.config.config import settings as app_config
from app.core.logger import Logger
from app.services import video_service
from app.services.audio_service import AudioService
from app.services.audio_stream_service import AudioStreamService
from app.services.battery_service import BatteryService
from app.services.camera_service import CameraService
from app.services.connection_service import ConnectionService
from app.services.detection_service import DetectionService
from app.services.file_service import FileService
from app.services.gstreamer_service import GStreamerService
from app.services.music_service import MusicService
from app.services.picamera2_service import PicameraService
from app.services.stream_service import StreamService
from app.services.tts_service import TTSService
from app.services.v4l2_service import V4L2Service
from app.services.video_recorder_service import VideoRecorderService
from app.services.video_service import VideoService
from fastapi import Depends

logger = Logger(__name__)


@lru_cache()
def get_connection_service() -> ConnectionService:
    return ConnectionService()


@lru_cache()
def get_detection_notifier() -> ConnectionService:
    return ConnectionService()


@lru_cache()
def get_video_service() -> VideoService:
    user_videos_dir = app_config.PX_VIDEO_DIR
    video_cache_path = app_config.VIDEO_CACHE_FILE_PATH
    video_cache_preview_dir = app_config.VIDEO_CACHE_PREVIEW_DIR

    return VideoService(
        video_cache_path=video_cache_path,
        preview_cache_dir=video_cache_preview_dir,
        video_dir=user_videos_dir,
    )


def get_v4l2_service() -> V4L2Service:
    return V4L2Service()


def get_gstreamer_service() -> GStreamerService:
    return GStreamerService()


def get_picamera_service() -> PicameraService:
    return PicameraService()


def get_video_device_adapter(
    v4l2_service: V4L2Service = Depends(get_v4l2_service),
    gstreamer_service: GStreamerService = Depends(get_gstreamer_service),
    picam_service: PicameraService = Depends(get_picamera_service),
) -> VideoDeviceAdapter:
    return VideoDeviceAdapter(
        v4l2_service=v4l2_service,
        gstreamer_service=gstreamer_service,
        picam_service=picam_service,
    )


def get_audio_service() -> AudioService:
    return AudioService()


def get_audio_stream_service() -> AudioStreamService:
    return AudioStreamService()


def get_file_manager(
    audio_service: AudioService = Depends(get_audio_service),
    video_service: VideoService = Depends(get_video_service),
) -> FileService:
    return FileService(audio_service=audio_service, video_service=video_service)


def get_video_recorder_service(
    file_manager: FileService = Depends(get_file_manager),
    video_service: VideoService = Depends(get_video_service),
) -> VideoRecorderService:
    return VideoRecorderService(file_manager=file_manager, video_service=video_service)


def get_detection_service(
    file_manager: FileService = Depends(get_file_manager),
    connection_manager: ConnectionService = Depends(get_connection_service),
) -> DetectionService:
    return DetectionService(
        file_manager=file_manager,
        connection_manager=connection_manager,
    )


def get_camera_service(
    detection_service: DetectionService = Depends(get_detection_service),
    file_manager: FileService = Depends(get_file_manager),
    connection_manager: ConnectionService = Depends(get_connection_service),
    video_device_adapter: VideoDeviceAdapter = Depends(get_video_device_adapter),
    video_recorder: VideoRecorderService = Depends(get_video_recorder_service),
) -> CameraService:
    return CameraService(
        detection_service=detection_service,
        file_manager=file_manager,
        connection_manager=connection_manager,
        video_device_adapter=video_device_adapter,
        video_recorder=video_recorder,
    )


def get_stream_service(
    camera_manager: CameraService = Depends(get_camera_service),
) -> StreamService:
    return StreamService(camera_service=camera_manager)


def get_music_service(
    file_manager: FileService = Depends(get_file_manager),
    connection_manager: ConnectionService = Depends(get_connection_service),
) -> MusicService:
    return MusicService(
        file_manager=file_manager,
        connection_manager=connection_manager,
    )


def get_tts_service() -> TTSService:
    return TTSService()


def get_battery_service(
    connection_manager: ConnectionService = Depends(get_connection_service),
    file_manager: FileService = Depends(get_file_manager),
) -> BatteryService:
    return BatteryService(
        connection_manager=connection_manager,
        file_manager=file_manager,
    )
