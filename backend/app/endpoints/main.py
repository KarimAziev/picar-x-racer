from app.util.logger import Logger
from quart import Blueprint, current_app, send_from_directory

main_bp = Blueprint("main", __name__)

logger = Logger(__name__)


async def index():
    template_folder = current_app.template_folder
    if isinstance(template_folder, str):
        return await send_from_directory(template_folder, "index.html")
    raise ValueError("Template folder is not a valid path.")


@main_bp.route("/", defaults={"path": ""})
@main_bp.route("/<path:path>")
async def catch_all(path):
    logger.info(f"catched path {path}")
    return await index()
