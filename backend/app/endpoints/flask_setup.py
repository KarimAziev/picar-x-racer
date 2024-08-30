from flask import Flask
from flask_cors import CORS
from typing import TYPE_CHECKING
from app.util.os_checks import is_raspberry_pi

if TYPE_CHECKING:
    from app.controllers.video_car_controller import VideoCarController
    from app.controllers.video_stream import VideoStreamManager


def create_app(
    controller: "VideoCarController", video_stream_manager: "VideoStreamManager"
):
    app = Flask(
        __name__,
        static_folder=controller.STATIC_FOLDER,
        template_folder=controller.TEMPLATE_FOLDER,
    )
    CORS(app)
    app.config["IS_RASPBERRY_PI"] = is_raspberry_pi()

    from app.endpoints.video_feed import video_feed_bp
    from app.endpoints.file_management import file_management_bp
    from app.endpoints.settings import settings_bp
    from app.endpoints.qrcode_routes import qrcode_bp
    from app.endpoints.battery import battery_bp
    from app.endpoints.main import main_bp

    app.register_blueprint(video_feed_bp)
    app.register_blueprint(qrcode_bp)
    app.register_blueprint(file_management_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(battery_bp)
    app.register_blueprint(main_bp)

    app.config["vc"] = controller
    app.config["video_manager"] = video_stream_manager

    return app


def run_flask(vc: "VideoCarController", video_stream_manager: "VideoStreamManager"):
    app = create_app(controller=vc, video_stream_manager=video_stream_manager)
    app.run(host="0.0.0.0", port=9000, threaded=True, debug=False)
