import asyncio
import threading
from multiprocessing import Process

from app.config.paths import PICARX_CONFIG_FILE, PICARX_OLD_CONFIG_FILE
from app.controllers.audio_controller import AudioController
from app.controllers.camera_controller import CameraController
from app.controllers.car_controller import CarController
from app.controllers.files_controller import FilesController
from app.controllers.stream_controller import StreamController
from app.endpoints.flask_setup import run_flask
from app.util.file_util import copy_file_if_not_exists
from app.util.logger import Logger

logger = Logger(__name__)

Logger.set_global_log_level(Logger.DEBUG)


def main():
    copy_file_if_not_exists(PICARX_OLD_CONFIG_FILE, PICARX_CONFIG_FILE)
    camera_manager = CameraController()
    stream_controller = StreamController(camera_controller=camera_manager, port=8050)
    audio_manager = AudioController()
    file_manager = FilesController(audio_manager=audio_manager)

    car_manager = CarController()

    # Start the Flask server in a separate thread
    flask_thread = threading.Thread(
        target=run_flask,
        args=(
            car_manager,
            camera_manager,
            file_manager,
            audio_manager,
            9000,
            True,
            False,
        ),
    )
    flask_thread.daemon = True
    flask_thread.start()

    # Start the StreamController in a separate process
    car_manager_process = Process(target=car_manager.run_server)
    car_manager_process.start()

    try:
        asyncio.run(stream_controller.run_streaming_server())
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    finally:
        car_manager_process.terminate()
        car_manager_process.join()
        flask_thread.join()
