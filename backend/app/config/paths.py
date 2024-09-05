from os import getlogin, path

from platformdirs import user_config_dir

user = getlogin()
user_home = path.expanduser(f"~{user}")

DEFAULT_PICTURES_PATH = "%s/Pictures/picar-x-racer/" % user_home
DEFAULT_VIDEOS_PATH = "%s/Videos/picar-x-racer/" % user_home

CURRENT_DIR = path.dirname(path.realpath(__file__))
PROJECT_DIR = path.dirname(path.dirname(path.dirname(CURRENT_DIR)))


def expand_file_in_project_dir(file: str):
    return path.abspath(path.join(PROJECT_DIR, file))


DEFAULT_USER_SETTINGS = path.abspath(path.join(PROJECT_DIR, "user_settings.json"))
DEFAULT_MUSIC_DIR = expand_file_in_project_dir("music")
DEFAULT_SOUND_DIR = expand_file_in_project_dir("sounds")
SETTINGS_FILE_PATH = path.abspath(path.join(PROJECT_DIR, "user_settings.json"))
MUSIC_DIR = expand_file_in_project_dir("music")
SOUNDS_DIR = expand_file_in_project_dir("sounds")
PHOTOS_DIR = expand_file_in_project_dir("photos")
STATIC_FOLDER = expand_file_in_project_dir("frontend/dist/assets")
TEMPLATE_FOLDER = expand_file_in_project_dir("frontend/dist")
CONFIG_USER_DIR = user_config_dir()
PICARX_CONFIG_DIR = path.join(CONFIG_USER_DIR, "picar-x")
PICARX_CONFIG_FILE = path.join(PICARX_CONFIG_DIR, "picar-x.conf")
ROBOT_HAT_CONFIG_FILE = path.join(PICARX_CONFIG_DIR, "robot-hat.conf")
PICARX_OLD_CONFIG_FILE = "/opt/picar-x/picar-x.conf"

CAT_FACE_CASCADE_PATH = expand_file_in_project_dir(
    "data/haarcascades/haarcascade_frontalcatface.xml"
)
HUMAN_FACE_CASCADE_PATH = expand_file_in_project_dir(
    "data/haarcascades/haarcascade_frontalface_default.xml"
)
HUMAN_FULL_BODY_CASCADE_PATH = expand_file_in_project_dir(
    "data/haarcascades/haarcascade_fullbody.xml"
)
HUMAN_FACE_CASCADE_PATH_EXTENDED = expand_file_in_project_dir(
    "data/haarcascades/haarcascade_frontalface_default.xml"
)
CAT_FACE_EXTENDED_CASCADE_PATH = expand_file_in_project_dir(
    "data/haarcascades/haarcascade_frontalcatface_extended.xml"
)

FONT_PATH = expand_file_in_project_dir(
    "frontend/src/assets/font/tt-octosquares-regular.ttf"
)
