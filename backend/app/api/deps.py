from app.services.audio_service import AudioService
from app.services.camera_service import CameraService
from app.services.detection_service import DetectionService
from app.services.files_service import FilesService
from app.services.stream_service import StreamService

detection_manager = DetectionService()
camera_manager = CameraService(detection_service=detection_manager)
stream_manager = StreamService(camera_service=camera_manager)
audio_manager = AudioService()
file_manager = FilesService(audio_manager=audio_manager)


def get_camera_manager() -> "CameraService":
    return camera_manager


def get_stream_manager() -> "StreamService":
    return stream_manager


def get_audio_manager() -> "AudioService":
    return audio_manager


def get_file_manager() -> "FilesService":
    return file_manager


def get_detection_manager() -> "DetectionService":
    return detection_manager
