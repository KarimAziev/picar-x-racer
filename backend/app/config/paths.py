from os import getenv, getlogin, path

from app.util.file_util import resolve_absolute_path
from platformdirs import user_config_dir

USER = getlogin()
USER_HOME = path.expanduser(f"~{USER}")

# where to save captured photos
PX_PHOTO_DIR = getenv("PX_PHOTO_DIR", "%s/Pictures/picar-x-racer/" % USER_HOME)

# where to save recordered videos
PX_VIDEO_DIR = getenv("PX_VIDEO_DIR", "%s/Videos/picar-x-racer/" % USER_HOME)

# where to save uploaded music
PX_MUSIC_DIR = getenv("PX_MUSIC_DIR", "%s/Music/picar-x-racer/music/" % USER_HOME)


CONFIG_USER_DIR = user_config_dir()

CURRENT_DIR = path.dirname(path.realpath(__file__))
PROJECT_DIR = path.dirname(path.dirname(path.dirname(CURRENT_DIR)))


DATA_DIR = path.join(PROJECT_DIR, "data")

DEFAULT_USER_SETTINGS = resolve_absolute_path("user_settings.json", PROJECT_DIR)
DEFAULT_MUSIC_DIR = resolve_absolute_path("music", PROJECT_DIR)

FRONTEND_FOLDER = resolve_absolute_path("frontend", PROJECT_DIR)
STATIC_FOLDER = resolve_absolute_path("frontend/dist/assets", PROJECT_DIR)
TEMPLATE_FOLDER = resolve_absolute_path("frontend/dist", PROJECT_DIR)

FONT_PATH = resolve_absolute_path(
    "frontend/src/assets/font/tt-octosquares-regular.ttf", PROJECT_DIR
)

MUSIC_CACHE_FILE_PATH = path.join(CONFIG_USER_DIR, "picar-x-racer/music_cache.json")

PICARX_CONFIG_DIR = path.join(CONFIG_USER_DIR, "picar-x")
PICARX_CONFIG_FILE = path.join(PICARX_CONFIG_DIR, "picar-x.conf")
PICARX_OLD_CONFIG_FILE = "/opt/picar-x/picar-x.conf"

YOLO_MODEL_PATH = resolve_absolute_path(
    getenv(
        "YOLO_MODEL_PATH",
        "yolov8n.pt",
    ),
    DATA_DIR,
)


YOLO_MODEL_EDGE_TPU_PATH = resolve_absolute_path(
    getenv(
        "YOLO_MODEL_EDGE_TPU_PATH",
        "yolov8n_320_edgetpu.tflite",
    ),
    DATA_DIR,
)
