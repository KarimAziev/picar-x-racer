import threading

from app.config.paths import PICARX_CONFIG_FILE, PICARX_OLD_CONFIG_FILE
from app.controllers.audio_controller import AudioController
from app.controllers.camera_controller import CameraController
from app.controllers.car_controller import CarController
from app.controllers.files_controller import FilesController
from app.endpoints.flask_setup import run_flask
from app.util.file_util import copy_file_if_not_exists
from app.util.logger import Logger

logger = Logger(__name__)

Logger.set_global_log_level(Logger.DEBUG)


def run_app():
    try:
        copy_file_if_not_exists(PICARX_OLD_CONFIG_FILE, PICARX_CONFIG_FILE)
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
    except KeyboardInterrupt as e:
        logger.info("Stopping application")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.log_exception("Cancelled", e)


if __name__ == "__main__":
    run_app()
