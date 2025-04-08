import json
import os
import re
import shutil
import tempfile
import zipfile
from io import BytesIO
from os import path
from pathlib import Path
from typing import Callable, List, Optional, Tuple, TypeVar, Union

from app.util.mime_type_helper import guess_mime_type

T = TypeVar("T")


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


def zip_files_generator(
    filenames: List[str], directory_fn: Callable[[str], str]
) -> Tuple[BytesIO, int]:
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for filename in filenames:
            root = directory_fn(filename)
            file_path = resolve_absolute_path(filename, root)

            if os.path.isdir(file_path):
                for dirpath, _, files in os.walk(file_path):
                    rel_dir = os.path.relpath(dirpath, root)
                    if rel_dir != ".":
                        zip_dir_name = rel_dir.replace(os.path.sep, "/") + "/"
                        zipf.writestr(zip_dir_name, "")
                    for f in files:
                        full_path = os.path.join(dirpath, f)
                        rel_file = os.path.join(os.path.relpath(dirpath, root), f)
                        archive_name = rel_file.replace(os.path.sep, "/")
                        with open(full_path, "rb") as fileobj:
                            zipf.writestr(archive_name, fileobj.read())

            elif os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    zipf.writestr(file_to_relative(file_path, root), f.read())
            else:
                continue

    buffer.seek(0)
    return buffer, len(buffer.getvalue())


def generate_zip_tempfile(
    filenames: List[str], directory_fn: Callable[[str], str]
) -> Tuple[str, int]:
    """
    Creates a temporary ZIP file containing the given filenames.

    Args:
        filenames: A list of filenames to include in the ZIP.
        directory_fn: A function that returns the directory path for each filename.

    Returns:
        A tuple containing the temporary file path and the file's size in bytes.
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    with zipfile.ZipFile(temp_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename in filenames:
            file_path = os.path.join(directory_fn(filename), filename)
            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    zipf.writestr(filename, f.read())

    temp_file.close()
    return temp_file.name, os.path.getsize(temp_file.name)


def file_details(filename: str, directory: Optional[str] = None):
    content_type = guess_mime_type(filename)
    file_stat = Path(filename).stat()
    file_mod_time = file_stat.st_mtime
    file_size = file_stat.st_size
    return {
        "content_type": content_type,
        "path": filename,
        "name": (
            file_to_relative(filename, directory) if directory is not None else filename
        ),
        "file_size": file_size,
        "modified": file_mod_time,
    }


def expand_home_dir(directory: str):
    if directory.startswith("~"):
        directory = os.path.expanduser(directory)
    return directory


def directory_files_recursively(
    directory: str,
    regexp: Optional[str] = None,
    include_directories: Optional[bool] = False,
    predicate: Optional[Callable[[str], bool]] = None,
    file_processor: Callable[[str, str], T] = file_details,
) -> List[T]:
    if directory.startswith("~"):
        directory = os.path.expanduser(directory)

    if not os.path.exists(directory):
        return []

    pattern = re.compile(regexp) if regexp is not None else None

    result: List[T] = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)

            if pattern and not pattern.search(file_path):
                continue

            if (not include_directories and os.path.isfile(file_path)) or (
                include_directories
                and (predicate(file_path) if predicate is not None else True)
            ):
                details = file_processor(file_path, directory)
                if details is not None:
                    result.append(details)
    return result


def abbreviate_path(path: str) -> str:
    home = os.path.expanduser("~")
    if home == os.path.sep:
        return path
    if path.startswith(home):
        if path == home:
            return "~"
        return "~" + path[len(home) :]
    return path


def exclude_nested_files(filenames: List[str]) -> List[Path]:
    paths = [Path(p).resolve() for p in filenames]

    directories = {p for p in paths if p.is_dir()}

    result = []
    for p in paths:
        if p.is_file() and any(parent in directories for parent in p.parents):
            continue
        result.append(p)
    return result


def file_in_directory(file: str, dir: str) -> bool:
    parents = Path(file).parents

    return dir in [item.as_posix() for item in parents]
