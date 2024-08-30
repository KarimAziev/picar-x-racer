from flask import Blueprint, send_from_directory, current_app
from app.config.logging_config import setup_logger

main_bp = Blueprint("main", __name__)

logger = setup_logger(__name__)


def index():
    template_folder = current_app.template_folder
    if isinstance(template_folder, str):
        return send_from_directory(template_folder, "index.html")
    raise ValueError("Template folder is not a valid path.")


@main_bp.route("/", defaults={"path": ""})
@main_bp.route("/<path:path>")
def catch_all(path):
    logger.info(f"catched path {path}")
    return index()
