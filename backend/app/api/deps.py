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

connection_manager = ConnectionService()
audio_manager = AudioService()
audio_stream_manager = AudioStreamService()
file_manager = FileService(audio_manager=audio_manager)
detection_manager = DetectionService(
    file_manager=file_manager, connection_manager=connection_manager
)
camera_manager = CameraService(
    detection_service=detection_manager,
    file_manager=file_manager,
    connection_manager=connection_manager,
)
stream_manager = StreamService(camera_service=camera_manager)
music_manager = MusicService(
    file_manager=file_manager, connection_manager=connection_manager
)

tts_manager = TTSService()
battery_manager = BatteryService(
    connection_manager=connection_manager, file_manager=file_manager
)


def get_camera_manager() -> CameraService:
    return camera_manager


def get_stream_manager() -> StreamService:
    return stream_manager


def get_audio_manager() -> AudioService:
    return audio_manager


def get_file_manager() -> FileService:
    return file_manager


def get_detection_manager() -> DetectionService:
    return detection_manager


def get_music_manager() -> MusicService:
    return music_manager


def get_tts_manager() -> TTSService:
    return tts_manager


def get_audio_stream_service() -> AudioStreamService:
    return audio_stream_manager


def get_battery_manager() -> BatteryService:
    return battery_manager
