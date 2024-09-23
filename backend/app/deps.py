from app.controllers.audio_controller import AudioController
from app.controllers.camera_controller import CameraController
from app.controllers.car_controller import CarController
from app.controllers.detection_controller import DetectionController
from app.controllers.files_controller import FilesController
from app.controllers.stream_controller import StreamController

detection_manager = DetectionController()
camera_manager = CameraController(detection_controller=detection_manager)
stream_manager = StreamController(camera_controller=camera_manager)
audio_manager = AudioController()
file_manager = FilesController(audio_manager=audio_manager)
car_manager = CarController()


def get_camera_manager() -> "CameraController":
    return camera_manager


def get_car_manager() -> "CarController":
    return car_manager


def get_stream_manager() -> "StreamController":
    return stream_manager


def get_audio_manager() -> "AudioController":
    return audio_manager


def get_file_manager() -> "FilesController":
    return file_manager


def get_detection_manager() -> "DetectionController":
    return detection_manager
