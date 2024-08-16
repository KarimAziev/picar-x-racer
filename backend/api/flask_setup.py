from flask import Flask
from flask_cors import CORS
from typing import TYPE_CHECKING
from util.os_checks import is_raspberry_pi

if TYPE_CHECKING:
    from controllers.video_car_controller import VideoCarController


def create_app(controller: "VideoCarController"):
    app = Flask(
        __name__,
        static_folder=controller.STATIC_FOLDER,
        template_folder=controller.TEMPLATE_FOLDER,
    )
    CORS(app)
    app.config["IS_RASPBERRY_PI"] = is_raspberry_pi()

    from api.video_feed import video_feed_bp
    from api.file_management import file_management_bp
    from api.settings import settings_bp
    from api.qrcode_routes import qrcode_bp
    from api.main import main_bp

    app.register_blueprint(video_feed_bp)
    app.register_blueprint(qrcode_bp)
    app.register_blueprint(file_management_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(main_bp)

    app.config["UPLOAD_FOLDER"] = controller.UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max file size
    app.config["vc"] = controller

    return app


def run_flask(vc: "VideoCarController"):
    app = create_app(vc)
    app.run(host="0.0.0.0", port=9000, threaded=True, debug=False)
