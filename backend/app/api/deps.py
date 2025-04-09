import os
from functools import lru_cache
from typing import Annotated, AsyncGenerator, Dict, TypedDict

from app.adapters.video_device_adapter import VideoDeviceAdapter
from app.config.config import settings as app_config
from app.core.logger import Logger
from app.managers.file_management.file_manager import FileManager
from app.schemas.file_management import AliasDir
from app.schemas.music import MusicPlayerMode
from app.services.camera.camera_service import CameraService
from app.services.camera.gstreamer_service import GStreamerService
from app.services.camera.picamera2_service import PicameraService
from app.services.camera.stream_service import StreamService
from app.services.camera.v4l2_service import V4L2Service
from app.services.connection_service import ConnectionService
from app.services.detection.detection_file_service import DetectionFileService
from app.services.detection.detection_service import DetectionService
from app.services.domain.settings_service import SettingsService
from app.services.file_management.file_filter_service import FileFilterService
from app.services.file_management.file_manager_service import FileManagerService
from app.services.integration.robot_communication_service import (
    RobotCommunicationService,
)
from app.services.media.audio_service import AudioService
from app.services.media.audio_stream_service import AudioStreamService
from app.services.media.music_file_service import MusicFileService
from app.services.media.music_service import MusicService
from app.services.media.tts_service import TTSService
from app.services.media.video_recorder_service import VideoRecorderService
from fastapi import Depends, Path

logger = Logger(__name__)


@lru_cache()
def get_connection_service() -> ConnectionService:
    return ConnectionService()


@lru_cache()
def get_detection_notifier() -> ConnectionService:
    return ConnectionService()


def get_v4l2_service() -> V4L2Service:
    return V4L2Service()


def get_gstreamer_service() -> GStreamerService:
    return GStreamerService()


def get_picamera_service() -> PicameraService:
    return PicameraService()


def get_video_device_adapter(
    v4l2_service: Annotated[V4L2Service, Depends(get_v4l2_service)],
    gstreamer_service: Annotated[GStreamerService, Depends(get_gstreamer_service)],
    picam_service: Annotated[PicameraService, Depends(get_picamera_service)],
) -> VideoDeviceAdapter:
    return VideoDeviceAdapter(
        v4l2_service=v4l2_service,
        gstreamer_service=gstreamer_service,
        picam_service=picam_service,
    )


def get_robot_communication_service() -> RobotCommunicationService:
    control_port = os.getenv("PX_CONTROL_APP_PORT", "8001")
    return RobotCommunicationService(base_url=f"http://127.0.0.1:{control_port}")


@lru_cache()
def get_audio_service() -> AudioService:
    return AudioService()


@lru_cache()
def get_audio_stream_service() -> AudioStreamService:
    return AudioStreamService()


def get_custom_file_manager() -> FileManager:
    return FileManager()


def get_file_filter_service() -> FileFilterService:
    return FileFilterService()


@lru_cache()
def get_photo_file_manager(
    file_manager: Annotated[FileManager, Depends(get_custom_file_manager)],
    filter_service: Annotated[FileFilterService, Depends(get_file_filter_service)],
) -> FileManagerService:
    return FileManagerService(
        root_directory=app_config.PX_PHOTO_DIR,
        cache_dir=os.path.join(app_config.PX_CACHE_DIR, "Pictures"),
        file_manager=file_manager,
        filter_service=filter_service,
    )


@lru_cache()
def get_video_file_manager(
    file_manager: Annotated[FileManager, Depends(get_custom_file_manager)],
    filter_service: Annotated[FileFilterService, Depends(get_file_filter_service)],
) -> FileManagerService:
    return FileManagerService(
        root_directory=app_config.PX_VIDEO_DIR,
        cache_dir=os.path.join(app_config.PX_CACHE_DIR, "Video"),
        file_manager=file_manager,
        filter_service=filter_service,
    )


@lru_cache()
def get_data_file_manager(
    file_manager: Annotated[FileManager, Depends(get_custom_file_manager)],
    filter_service: Annotated[FileFilterService, Depends(get_file_filter_service)],
) -> FileManagerService:
    return DetectionFileService(
        root_directory=app_config.DATA_DIR,
        cache_dir=os.path.join(app_config.PX_CACHE_DIR, "data"),
        file_manager=file_manager,
        filter_service=filter_service,
    )


def get_settings_service() -> SettingsService:
    return SettingsService()


def get_music_service(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    connection_manager: Annotated[ConnectionService, Depends(get_connection_service)],
) -> MusicService:
    return MusicService(
        connection_manager=connection_manager,
        music_dir=app_config.PX_MUSIC_DIR,
        default_music_dir=app_config.DEFAULT_MUSIC_DIR,
        tracks=[],
        mode=settings_service.load_settings().get("mode") or MusicPlayerMode.LOOP,
    )


@lru_cache()
def get_music_file_service(
    file_manager: Annotated[FileManager, Depends(get_custom_file_manager)],
    filter_service: Annotated[FileFilterService, Depends(get_file_filter_service)],
    music_service: Annotated[MusicService, Depends(get_music_service)],
) -> MusicFileService:
    return MusicFileService(
        default_music_dir=app_config.DEFAULT_MUSIC_DIR,
        root_directory=app_config.PX_MUSIC_DIR,
        cache_dir=os.path.join(app_config.PX_CACHE_DIR, "Music"),
        file_manager=file_manager,
        filter_service=filter_service,
        music_service=music_service,
    )


def get_directory_handlers(
    photo_file_manager: Annotated[FileManagerService, Depends(get_photo_file_manager)],
    video_file_manager: Annotated[FileManagerService, Depends(get_video_file_manager)],
    music_file_manager: Annotated[MusicFileService, Depends(get_music_file_service)],
    data_file_manager: Annotated[FileManagerService, Depends(get_data_file_manager)],
) -> Dict[AliasDir, FileManagerService]:
    handlers = {
        AliasDir.image: photo_file_manager,
        AliasDir.video: video_file_manager,
        AliasDir.music: music_file_manager,
        AliasDir.data: data_file_manager,
    }
    return handlers


def get_directory_handler_by_alias(
    alias_dir: Annotated[
        AliasDir, Path(description="Directory alias for application content")
    ],
    handlers: Annotated[
        Dict[AliasDir, FileManagerService], Depends(get_directory_handlers)
    ],
) -> FileManagerService:
    return handlers[alias_dir]


def get_video_recorder_service(
    file_manager: Annotated[FileManagerService, Depends(get_video_file_manager)],
) -> VideoRecorderService:
    return VideoRecorderService(file_manager=file_manager)


def get_detection_service(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    connection_manager: Annotated[ConnectionService, Depends(get_connection_service)],
    file_manager: Annotated[FileManagerService, Depends(get_data_file_manager)],
) -> DetectionService:
    return DetectionService(
        settings_service=settings_service,
        file_manager=file_manager,
        connection_manager=connection_manager,
    )


def get_camera_service(
    detection_service: Annotated[DetectionService, Depends(get_detection_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    connection_manager: Annotated[ConnectionService, Depends(get_connection_service)],
    video_device_adapter: Annotated[
        VideoDeviceAdapter, Depends(get_video_device_adapter)
    ],
    video_recorder: Annotated[
        VideoRecorderService, Depends(get_video_recorder_service)
    ],
) -> CameraService:
    return CameraService(
        detection_service=detection_service,
        settings_service=settings_service,
        connection_manager=connection_manager,
        video_device_adapter=video_device_adapter,
        video_recorder=video_recorder,
    )


def get_stream_service(
    camera_manager: Annotated[CameraService, Depends(get_camera_service)],
) -> StreamService:
    return StreamService(camera_service=camera_manager)


def get_tts_service() -> TTSService:
    return TTSService()


class LifespanAppDeps(TypedDict):
    connection_manager: ConnectionService
    detection_manager: DetectionService
    music_file_service: MusicFileService


async def get_lifespan_dependencies(
    connection_manager: Annotated[ConnectionService, Depends(get_connection_service)],
    detection_manager: Annotated[DetectionService, Depends(get_detection_service)],
    music_file_service: Annotated[MusicFileService, Depends(get_music_file_service)],
) -> AsyncGenerator[LifespanAppDeps, None]:
    deps: LifespanAppDeps = {
        "connection_manager": connection_manager,
        "detection_manager": detection_manager,
        "music_file_service": music_file_service,
    }
    yield deps
