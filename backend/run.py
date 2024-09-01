import logging
from app.util.file_util import copy_file_if_not_exists
import threading
from app.controllers.video_car_controller import VideoCarController
from app.controllers.video_stream import VideoStreamManager
from app.endpoints.flask_setup import run_flask
from app.config.paths import PICARX_CONFIG_FILE, PICARX_OLD_CONFIG_FILE
from app.controllers.video_car_controller import VideoCarController
from app.controllers.video_stream import VideoStreamManager
from app.controllers.audio_handler import AudioHandler
from app.controllers.files_controller import FilesController


copy_file_if_not_exists(PICARX_OLD_CONFIG_FILE, PICARX_CONFIG_FILE)
from app.util.logger import Logger

Logger.set_global_log_level(logging.DEBUG)

if __name__ == "__main__":
    controller = None
    video_manager = None
    try:
        file_manager = FilesController()
        audio_manager = AudioHandler()
        camera_manager = VideoStreamManager()
        car_manager = VideoCarController(
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
