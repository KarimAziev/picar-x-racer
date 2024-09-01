import shutil
import json
from os import path
import os


def copy_file_if_not_exists(source: str, target: str):
    """
    Copies a file from source to target if the target file does not exist.
    """
    if os.path.exists(source) and not os.path.exists(target):
        dir = os.path.dirname(target)
        if not os.path.exists(dir):
            os.makedirs(dir)
        shutil.copyfile(source, target)


def load_json_file(file: str):
    with open(file, "r") as f:
        return json.load(f)


def ensure_parent_dir_exists(file: str):
    dir = path.dirname(file)
    if not path.exists(dir):
        os.makedirs(dir)
