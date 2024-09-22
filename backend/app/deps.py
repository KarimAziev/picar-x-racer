from app.controllers.audio_controller import AudioController
from app.controllers.camera_controller import CameraController
from app.controllers.car_controller import CarController
from app.controllers.files_controller import FilesController
from app.controllers.stream_controller import StreamController

camera_manager = CameraController()
stream_controller = StreamController(camera_controller=camera_manager)
audio_manager = AudioController()
file_manager = FilesController(audio_manager=audio_manager)
car_manager = CarController()


def get_camera_manager() -> "CameraController":
    from app.controllers.camera_controller import CameraController

    return CameraController()


def get_car_manager() -> "CarController":
    return car_manager


def get_stream_manager() -> "StreamController":
    return stream_controller


def get_audio_manager() -> "AudioController":
    return audio_manager


def get_file_manager() -> "FilesController":
    return file_manager
