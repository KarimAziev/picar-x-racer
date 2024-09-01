import shutil
from os import makedirs, path


def copy_file_if_not_exists(source: str, target: str):
    """
    Copies a file from source to target if the target file does not exist.
    """
    if path.exists(target) and not path.exists(source):
        dir = path.dirname(target)
        if not path.exists(dir):
            makedirs(dir)
        shutil.copyfile(source, target)
