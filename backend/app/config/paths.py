from os import getenv, getlogin, path

from platformdirs import user_config_dir

user = getlogin()
user_home = path.expanduser(f"~{user}")

DEFAULT_PICTURES_PATH = "%s/Pictures/picar-x-racer/" % user_home
DEFAULT_VIDEOS_PATH = "%s/Videos/picar-x-racer/" % user_home


CURRENT_DIR = path.dirname(path.realpath(__file__))
PROJECT_DIR = path.dirname(path.dirname(path.dirname(CURRENT_DIR)))


def expand_file_in_project_dir(file: str):
    return path.abspath(path.join(PROJECT_DIR, file))


def ensure_absolute_path(file: str):
    if path.isabs(file):
        return file
    return path.abspath(path.join(PROJECT_DIR, file))


DEFAULT_USER_SETTINGS = path.abspath(path.join(PROJECT_DIR, "user_settings.json"))
APP_DIR = path.abspath(path.join(PROJECT_DIR, "backend/app"))
DEFAULT_MUSIC_DIR = expand_file_in_project_dir("music")
DEFAULT_SOUND_DIR = expand_file_in_project_dir("sounds")
SETTINGS_FILE_PATH = path.abspath(path.join(PROJECT_DIR, "user_settings.json"))
FRONTEND_FOLDER = expand_file_in_project_dir("frontend")
STATIC_FOLDER = expand_file_in_project_dir("frontend/dist/assets")
TEMPLATE_FOLDER = expand_file_in_project_dir("frontend/dist")
CONFIG_USER_DIR = user_config_dir()
FONT_PATH = expand_file_in_project_dir(
    "frontend/src/assets/font/tt-octosquares-regular.ttf"
)

MUSIC_DIR = expand_file_in_project_dir("music")
SOUNDS_DIR = expand_file_in_project_dir("sounds")
PHOTOS_DIR = expand_file_in_project_dir("photos")
PICARX_CONFIG_DIR = path.join(CONFIG_USER_DIR, "picar-x")
PICARX_CONFIG_FILE = path.join(PICARX_CONFIG_DIR, "picar-x.conf")
PICARX_OLD_CONFIG_FILE = "/opt/picar-x/picar-x.conf"


YOLO_MODEL_PATH = ensure_absolute_path(getenv("YOLO_MODEL_PATH", "data/yolo11n.pt"))

YOLO_MODEL_EDGE_TPU_PATH = ensure_absolute_path(
    getenv(
        "YOLO_MODEL_EDGE_TPU_PATH",
        "data/yolo11n_full_integer_quant_edgetpu.tflite",
    )
)
