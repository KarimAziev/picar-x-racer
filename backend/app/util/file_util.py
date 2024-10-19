import json
import os
import shutil
from os import path


def copy_file_if_not_exists(source: str, target: str):
    """
    Copies a file from source to target if the target file does not exist.
    """
    if os.path.exists(source) and not os.path.exists(target):
        ensure_parent_dir_exists(target)
        shutil.copyfile(source, target)


def load_json_file(file: str):
    """
    Load and parse a JSON file from the specified file path.

    Parameters:
    file (str): The file path of the JSON file to be loaded.

    Returns:
    dict: The contents of the JSON file parsed into a Python dictionary.

    Raises:
    FileNotFoundError: If the specified file does not exist.
    json.JSONDecodeError: If there is an error parsing the JSON from the file.

    Example:
    >>> data = load_json_file("data.json")
    """
    with open(file, "r") as f:
        return json.load(f)


def ensure_parent_dir_exists(file: str):
    """
    Ensure that the parent directory for the specified file exists.
    If the directory does not exist, it creates the necessary directories.

    Parameters:
    file (str): The complete path to the file whose parent directory should be checked or created.

    Example:
    >>> ensure_parent_dir_exists("/path/to/file.txt")
    # If "/path/to" does not exist, it will be created.
    """
    directory = path.dirname(file)
    if not path.exists(directory):
        os.makedirs(directory)


def resolve_absolute_path(file: str, *dir_segmens):
    """
    Resolve the file path either as an absolute path or relative to given directories.

    Args:
        file (str): The file name or relative path.
        dir_segments (str): Optional directory segments that compose the base path when the file is relative.

    Returns:
        str: The absolute file path. If the file path is already absolute, it is returned as-is.
             Otherwise, it is resolved relative to the provided directory segments.

    Example:
        If `file` is an absolute path like '/usr/bin/bash', it will be returned unchanged.

        If `file` is 'bash' and `dir_segments` is '/usr', 'bin', then '/usr/bin/bash' will be returned.
    """
    if path.isabs(file):
        return file
    return path.abspath(path.join(*dir_segmens, file))
