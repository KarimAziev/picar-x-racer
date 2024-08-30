from os import path, getlogin

user = getlogin()
user_home = path.expanduser(f"~{user}")

DEFAULT_PICTURES_PATH = "%s/Pictures/picar-x-racer/" % user_home
DEFAULT_VIDEOS_PATH = "%s/Videos/picar-x-racer/" % user_home

CURRENT_DIR = path.dirname(path.realpath(__file__))
PROJECT_DIR = path.dirname(path.dirname(path.dirname(CURRENT_DIR)))


def expand_file_in_project_dir(file: str):
    return path.abspath(path.join(PROJECT_DIR, file))


SETTINGS_FILE_PATH = path.abspath(path.join(PROJECT_DIR, "user_settings.json"))
MUSIC_DIR = expand_file_in_project_dir("music")
SOUNDS_DIR = expand_file_in_project_dir("sounds")
PHOTOS_DIR = expand_file_in_project_dir("photos")
STATIC_FOLDER = expand_file_in_project_dir("frontend/dist/assets")
TEMPLATE_FOLDER = expand_file_in_project_dir("frontend/dist")