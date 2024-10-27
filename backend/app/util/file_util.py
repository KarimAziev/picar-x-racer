import json
import os
import shutil
from os import path
from pathlib import Path
from typing import Tuple, Union


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
    if file.startswith("~"):
        file = os.path.expanduser(file)
    if path.isabs(file):
        return file
    return path.abspath(path.join(*dir_segmens, file))


def get_files_with_extension(directory: str, extension: Union[str, Tuple[str, ...]]):
    """
    Recursively scans the provided directory and returns all files with the specified extension.
    """
    result = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                result.append(os.path.join(root, file))

    return result


def file_name_parent_directory(directory: Union[Path, str]) -> Path:
    """
    Returns the parent directory of the given directory.

    Parameters:
    directory (Path or str): The directory whose parent is to be returned. It can be
                             provided as a Path object or as a string representing
                             the path.

    Returns:
    Path: A Path object representing the parent directory of the given directory.

    Example:
    >>> file_name_parent_directory("/home/user/documents")
    PosixPath('/home/user')

    >>> file_name_parent_directory(Path("/home/user/documents"))
    PosixPath('/home/user')
    """
    if isinstance(directory, Path):
        return directory.parent
    return Path(directory).parent


def get_directory_name(path: Union[Path, str]) -> str:
    """
    Returns the name of the directory or file, given a path.

    Parameters:
    path (Path or str): The path to extract the name from. It can be provided
                        either as a Path object or as a string representing
                        the path.

    Returns:
    str: The name of the file or directory at the given path.

    Example:
    >>> get_directory_name("/home/user/documents")
    'documents'

    >>> get_directory_name(Path("/home/user/documents"))
    'documents'
    """
    if isinstance(path, Path):
        return path.name
    return Path(path).name
