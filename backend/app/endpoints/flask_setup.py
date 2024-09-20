from typing import TYPE_CHECKING

from app.config.paths import STATIC_FOLDER, TEMPLATE_FOLDER
from app.util.logger import Logger
from app.util.os_checks import is_raspberry_pi
from quart import Quart
from quart_cors import cors

if TYPE_CHECKING:
    from app.controllers.audio_controller import AudioController
    from app.controllers.camera_controller import CameraController
    from app.controllers.car_controller import CarController
    from app.controllers.files_controller import FilesController
    from app.controllers.stream_controller import StreamController

logger = Logger(__name__)


def create_app(
    car_manager: "CarController",
    camera_manager: "CameraController",
    file_manager: "FilesController",
    audio_manager: "AudioController",
    stream_controller: "StreamController",
):
    app = Quart(
        __name__,
        static_folder=STATIC_FOLDER,
        template_folder=TEMPLATE_FOLDER,
    )
    cors(app)
    app.config["IS_RASPBERRY_PI"] = is_raspberry_pi()

    from app.endpoints.audio import audio_management_bp
    from app.endpoints.battery import battery_bp
    from app.endpoints.camera import camera_feed_bp
    from app.endpoints.car_control import car_controller_bp
    from app.endpoints.distance import distance_bp
    from app.endpoints.file_management import file_management_bp
    from app.endpoints.main import main_bp
    from app.endpoints.settings import settings_bp
    from app.endpoints.video_feed import video_feed_bp

    app.register_blueprint(video_feed_bp)
    app.register_blueprint(camera_feed_bp)
    app.register_blueprint(file_management_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(battery_bp)
    app.register_blueprint(audio_management_bp)
    app.register_blueprint(distance_bp)
    app.register_blueprint(car_controller_bp)
    app.register_blueprint(main_bp)
    app.config["car_manager"] = car_manager
    app.config["stream_controller"] = stream_controller
    app.config["file_manager"] = file_manager
    app.config["camera_manager"] = camera_manager
    app.config["audio_manager"] = audio_manager
    return app
