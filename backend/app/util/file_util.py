import json
import os
import shutil
from os import path
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union


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
    os.makedirs(directory, exist_ok=True)


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


def file_to_relative(filename: Union[str, Path], directory: Union[str, Path]) -> str:
    """
    Convert filename to be relative to directory.
    """
    return os.path.relpath(filename, directory)


def is_parent_directory(parent_dir: str, file_path: str):
    """
    Check if a given directory is a parent (or ancestor) of a specified file
    or directory, or if it is the same directory as the file path provided.

    This function resolves both the parent directory and the file path to
    their absolute canonical paths before performing the check. It returns
    True if `parent_dir` is an ancestor directory of `file_path` or if
    `parent_dir` is the same as `file_path`, after resolving both paths. If
    the file or directory does not exist, the function will return False.

    Args:
        parent_dir (str): The path to the potential parent directory.
        file_path (str): The path to the file or directory to compare.

    Returns:
        bool: True if `parent_dir` contains `file_path` or is the same as
              `file_path`, False otherwise. Returns False if either path
              does not exist.

    Raises:
        None: The function handles FileNotFoundError internally.

    Example:
        >>> is_parent_directory('/home/user', '/home/user/docs/file.txt')
        True
        >>> is_parent_directory('/home/user/docs', '/home/user/photos')
        False
    """
    parent = Path(parent_dir).resolve()
    file = Path(file_path).resolve()

    try:
        return parent in file.parents or parent == file
    except FileNotFoundError:
        return False


def get_directory_structure(
    initial_directory: str,
    extension: Optional[Union[str, Tuple[str, ...]]] = None,
    directory_suffix: Optional[Union[str, Tuple[str, ...]]] = None,
    exclude_empty_dirs=True,
    absolute=True,
    file_processor: Optional[Callable[[str], Any]] = None,
) -> list[Dict[str, Any]]:
    def walk_directory(current_path: str):
        children = []
        entries = sorted(
            os.listdir(current_path),
            key=lambda entry: (
                not os.path.isdir(os.path.join(current_path, entry)),
                entry,
            ),
        )

        for entry in entries:
            entry_path = os.path.join(current_path, entry)
            key_path = (
                entry_path
                if absolute
                else file_to_relative(entry_path, initial_directory)
            )
            is_directory = os.path.isdir(entry_path)
            if (
                is_directory
                and directory_suffix
                and entry_path.endswith(directory_suffix)
            ):
                children.append(
                    {
                        "key": key_path,
                        "label": entry,
                        "selectable": True,
                        "data": {"name": entry, "type": "Folder"},
                    }
                )
            elif is_directory:
                subchildren = walk_directory(entry_path)
                if not exclude_empty_dirs or len(subchildren) > 0:
                    children.append(
                        {
                            "key": key_path,
                            "label": entry,
                            "selectable": False,
                            "children": subchildren,
                            "data": {"name": entry, "type": "Folder"},
                        }
                    )
            elif extension is None or entry_path.endswith(extension):
                if file_processor is not None:
                    file_processor(entry_path)
                children.append(
                    {
                        "key": key_path,
                        "label": entry,
                        "selectable": True,
                        "data": {"name": entry, "type": "File"},
                    }
                )

        return children

    return walk_directory(initial_directory)
