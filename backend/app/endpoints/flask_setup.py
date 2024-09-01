from flask import Flask
from flask_cors import CORS
from typing import TYPE_CHECKING
from app.util.os_checks import is_raspberry_pi
from app.config.paths import TEMPLATE_FOLDER, STATIC_FOLDER

if TYPE_CHECKING:
    from app.controllers.car_controller import CarController
    from app.controllers.camera_controller import CameraController
    from app.controllers.audio_controller import AudioController
    from app.controllers.files_controller import FilesController


def create_app(
    car_manager: "CarController",
    camera_manager: "CameraController",
    file_manager: "FilesController",
    audio_manager: "AudioController",
):
    app = Flask(
        __name__,
        static_folder=STATIC_FOLDER,
        template_folder=TEMPLATE_FOLDER,
    )
    CORS(app)
    app.config["IS_RASPBERRY_PI"] = is_raspberry_pi()

    from app.endpoints.video_feed import video_feed_bp
    from app.endpoints.file_management import file_management_bp
    from app.endpoints.settings import settings_bp
    from app.endpoints.qrcode_routes import qrcode_bp
    from app.endpoints.battery import battery_bp
    from app.endpoints.audio import audio_management_bp
    from app.endpoints.main import main_bp

    app.register_blueprint(video_feed_bp)
    app.register_blueprint(qrcode_bp)
    app.register_blueprint(file_management_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(battery_bp)
    app.register_blueprint(audio_management_bp)
    app.register_blueprint(main_bp)

    app.config["car_manager"] = car_manager
    app.config["file_manager"] = file_manager
    app.config["camera_manager"] = camera_manager
    app.config["audio_manager"] = audio_manager

    return app


def run_flask(
    car_manager: "CarController",
    camera_manager: "CameraController",
    file_manager: "FilesController",
    audio_manager: "AudioController",
):
    app = create_app(
        car_manager=car_manager,
        camera_manager=camera_manager,
        file_manager=file_manager,
        audio_manager=audio_manager,
    )
    app.run(host="0.0.0.0", port=9000, threaded=True, debug=False)
