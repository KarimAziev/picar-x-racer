import logging
from app.util.file_util import copy_file_if_not_exists
import threading
from app.controllers.camera_controller import CameraController
from app.controllers.car_controller import CarController
from app.controllers.camera_controller import CameraController
from app.endpoints.flask_setup import run_flask
from app.config.paths import PICARX_CONFIG_FILE, PICARX_OLD_CONFIG_FILE
from app.controllers.audio_controller import AudioController
from app.controllers.files_controller import FilesController


copy_file_if_not_exists(PICARX_OLD_CONFIG_FILE, PICARX_CONFIG_FILE)
from app.util.logger import Logger

Logger.set_global_log_level(logging.INFO)

if __name__ == "__main__":
    controller = None
    video_manager = None
    try:
        file_manager = FilesController()
        audio_manager = AudioController()
        camera_manager = CameraController()
        car_manager = CarController(
            camera_manager=camera_manager,
            file_manager=file_manager,
            audio_manager=audio_manager,
        )
        flask_thread = threading.Thread(
            target=run_flask,
            args=(car_manager, camera_manager, file_manager, audio_manager),
        )
        flask_thread.daemon = True
        flask_thread.start()
        car_manager.main()
    except Exception as e:
        print(f"error: {e}")
    finally:
        if video_manager:
            video_manager.camera_close()
