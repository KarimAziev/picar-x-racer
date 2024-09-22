from typing import TYPE_CHECKING

from fastapi import Depends

if TYPE_CHECKING:
    from app.controllers.audio_controller import AudioController
    from app.controllers.camera_controller import CameraController
    from app.controllers.car_controller import CarController
    from app.controllers.files_controller import FilesController
    from app.controllers.stream_controller import StreamController


def get_camera_manager() -> "CameraController":
    from app.controllers.camera_controller import CameraController

    return CameraController()


def get_car_manager() -> "CarController":
    from app.controllers.car_controller import CarController

    return CarController()


def get_stream_manager(
    camera_manager: "CameraController" = Depends(get_camera_manager),
) -> "StreamController":
    from app.controllers.stream_controller import StreamController

    return StreamController(camera_controller=camera_manager)


def get_audio_manager() -> "AudioController":
    from app.controllers.audio_controller import AudioController

    return AudioController()


def get_file_manager(
    audio_manager: "AudioController" = Depends(get_audio_manager),
) -> "FilesController":
    from app.controllers.files_controller import FilesController

    return FilesController(audio_manager=audio_manager)
