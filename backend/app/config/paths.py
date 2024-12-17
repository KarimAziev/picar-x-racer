from os import getenv, path

from app.util.file_util import resolve_absolute_path
from platformdirs import (
    user_cache_dir,
    user_config_dir,
    user_music_dir,
    user_pictures_dir,
    user_videos_dir,
)

CONFIG_USER_DIR = user_config_dir()
CACHE_USER_DIR = user_cache_dir()
PICTURES_USER_DIR = user_pictures_dir()
MUSIC_USER_DIR = user_music_dir()
VIDEO_USER_DIR = user_videos_dir()

APP_NAME = "picar-x-racer"

# where to save captured photos
PX_PHOTO_DIR = getenv("PX_PHOTO_DIR", path.join(PICTURES_USER_DIR, APP_NAME))

# where to save recordered videos
PX_VIDEO_DIR = getenv("PX_VIDEO_DIR", path.join(VIDEO_USER_DIR, APP_NAME))

# where to save uploaded music
PX_MUSIC_DIR = getenv(
    "PX_MUSIC_DIR",
    path.join(
        MUSIC_USER_DIR,
        APP_NAME,
        "music",
    ),
)

PX_SETTINGS_FILE = getenv(
    "PX_SETTINGS_FILE", path.join(CONFIG_USER_DIR, APP_NAME, "user_settings.json")
)


CURRENT_DIR = path.dirname(path.realpath(__file__))
PROJECT_DIR = path.dirname(path.dirname(path.dirname(CURRENT_DIR)))


DATA_DIR = path.join(PROJECT_DIR, "data")

DEFAULT_USER_SETTINGS = resolve_absolute_path("user_settings.json", PROJECT_DIR)
DEFAULT_MUSIC_DIR = resolve_absolute_path("music", PROJECT_DIR)
DEFAULT_SOUNDS_DIR = resolve_absolute_path("sounds", PROJECT_DIR)

FRONTEND_FOLDER = resolve_absolute_path("frontend", PROJECT_DIR)
STATIC_FOLDER = resolve_absolute_path("frontend/dist/assets", PROJECT_DIR)
TEMPLATE_FOLDER = resolve_absolute_path("frontend/dist", PROJECT_DIR)

FONT_PATH = resolve_absolute_path(
    "frontend/src/assets/font/tt-octosquares-regular.ttf", PROJECT_DIR
)

MUSIC_CACHE_FILE_PATH = path.join(CACHE_USER_DIR, APP_NAME, "music_cache.json")

PICARX_CONFIG_DIR = path.join(CONFIG_USER_DIR, "picar-x")
ROBOT_HAT_CONF = path.join(CONFIG_USER_DIR, "robot-hat/robot-hat.conf")
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
