from flask import Blueprint, send_from_directory, current_app

main_bp = Blueprint("main", __name__)


def index():
    template_folder = current_app.template_folder
    if isinstance(template_folder, str):
        return send_from_directory(template_folder, "index.html")
    raise ValueError("Template folder is not a valid path.")


@main_bp.route("/", defaults={"path": ""})
@main_bp.route("/<path:path>")
def catch_all(path):
    return index()
