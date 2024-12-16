from functools import lru_cache

from app.adapters.video_device_adapter import VideoDeviceAdapater
from app.services.audio_service import AudioService
from app.services.audio_stream_service import AudioStreamService
from app.services.battery_service import BatteryService
from app.services.camera_service import CameraService
from app.services.connection_service import ConnectionService
from app.services.detection_service import DetectionService
from app.services.file_service import FileService
from app.services.music_service import MusicService
from app.services.stream_service import StreamService
from app.services.tts_service import TTSService
from app.services.video_recorder import VideoRecorder
from app.util.logger import Logger
from fastapi import Depends

logger = Logger(__name__)


@lru_cache()
def get_connection_manager() -> ConnectionService:
    return ConnectionService()


@lru_cache()
def get_detection_notifier() -> ConnectionService:
    return ConnectionService()


def get_video_device_adapter() -> VideoDeviceAdapater:
    return VideoDeviceAdapater()


def get_audio_manager() -> AudioService:
    return AudioService()


def get_audio_stream_service() -> AudioStreamService:
    return AudioStreamService()


def get_file_manager(
    audio_manager: AudioService = Depends(get_audio_manager),
) -> FileService:
    return FileService(audio_manager=audio_manager)


def get_video_recorder(
    file_manager: FileService = Depends(get_file_manager),
) -> VideoRecorder:
    return VideoRecorder(file_manager=file_manager)


def get_detection_manager(
    file_manager: FileService = Depends(get_file_manager),
    connection_manager: ConnectionService = Depends(get_connection_manager),
) -> DetectionService:
    return DetectionService(
        file_manager=file_manager,
        connection_manager=connection_manager,
    )


def get_camera_manager(
    detection_service: DetectionService = Depends(get_detection_manager),
    file_manager: FileService = Depends(get_file_manager),
    connection_manager: ConnectionService = Depends(get_connection_manager),
    video_device_adapter: VideoDeviceAdapater = Depends(get_video_device_adapter),
    video_recorder: VideoRecorder = Depends(get_video_recorder),
) -> CameraService:
    return CameraService(
        detection_service=detection_service,
        file_manager=file_manager,
        connection_manager=connection_manager,
        video_device_adapter=video_device_adapter,
        video_recorder=video_recorder,
    )


def get_stream_manager(
    camera_manager: CameraService = Depends(get_camera_manager),
) -> StreamService:
    return StreamService(camera_service=camera_manager)


def get_music_manager(
    file_manager: FileService = Depends(get_file_manager),
    connection_manager: ConnectionService = Depends(get_connection_manager),
) -> MusicService:
    return MusicService(
        file_manager=file_manager,
        connection_manager=connection_manager,
    )


def get_tts_manager() -> TTSService:
    return TTSService()


def get_battery_manager(
    connection_manager: ConnectionService = Depends(get_connection_manager),
    file_manager: FileService = Depends(get_file_manager),
) -> BatteryService:
    return BatteryService(
        connection_manager=connection_manager,
        file_manager=file_manager,
    )
