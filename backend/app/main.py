import asyncio

from hypercorn.asyncio import serve
from hypercorn.config import Config

from app.config.paths import PICARX_CONFIG_FILE, PICARX_OLD_CONFIG_FILE
from app.controllers.audio_controller import AudioController
from app.controllers.camera_controller import CameraController
from app.controllers.car_controller import CarController
from app.controllers.files_controller import FilesController
from app.controllers.stream_controller import StreamController
from app.endpoints.flask_setup import create_app
from app.util.file_util import copy_file_if_not_exists
from app.util.get_ip_address import get_ip_address
from app.util.logger import Logger

logger = Logger(__name__)


def setup_logger(log_level="INFO"):
    log_level = log_level.upper()
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_log_levels:
        print(f"Invalid log level: {log_level}. Using DEBUG.")
        log_level = "DEBUG"

    log_level_constant = getattr(Logger, log_level, Logger.DEBUG)
    Logger.set_global_log_level(log_level_constant)


def main(debug: bool = False, log_level="INFO"):
    setup_logger(log_level=log_level)

    copy_file_if_not_exists(PICARX_OLD_CONFIG_FILE, PICARX_CONFIG_FILE)

    camera_manager = CameraController()
    stream_controller = StreamController(camera_controller=camera_manager)
    audio_manager = AudioController()
    file_manager = FilesController(audio_manager=audio_manager)
    car_manager = CarController()
    app = create_app(
        car_manager=car_manager,
        camera_manager=camera_manager,
        audio_manager=audio_manager,
        file_manager=file_manager,
        stream_controller=stream_controller,
    )

    config = Config()
    config.bind = ["0.0.0.0:9000"]
    config.use_reloader = False
    config.debug = debug
    ip_address = get_ip_address()

    logger.info(
        f"\nTo access the frontend, open your browser and navigate to http://{ip_address}:9000\n"
    )

    try:
        asyncio.run(serve(app, config))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received shutdown signal, shutting down.")
        # Clean up resources
        try:
            asyncio.run(camera_manager.stop_camera())
            # Stop other managers if necessary
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    finally:
        logger.info("Application shutdown complete.")
