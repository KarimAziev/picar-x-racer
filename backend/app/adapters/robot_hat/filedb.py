import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, TypeVar, Union

from app.util.logger import Logger

T = TypeVar('T')

logger = Logger(__name__)


@dataclass
class FileDB(object):
    """
    A lightweight file-based key-value database.

    This class provides an easy way to store, retrieve, and manage key-value
    pairs in a simple text file. It's convenient for handling configuration
    files and calibration values for robots or similar applications.

    Example file format:
        # robot-hat configuration file
        speed = 100
        calibration = 1.23
    """

    db: str

    def __post_init__(self):
        """
        Ensures that the database file exists when the class is initialized.

        If the file doesn't exist, it will be created, along with necessary
        parent directories. A default comment header will also be written.
        """
        if not self.db:
            raise ValueError("db: Missing file path parameter.")
        FileDB.file_check_create(self.db)

    @staticmethod
    def file_check_create(
        file: str,
    ) -> None:
        """
        Ensures the specified file exists.

        If the file doesn't exist, it creates the file and its parent directories
        as needed. Adds a simple header to newly created files. If something
        already exists with the same name but it's a directory, raises an error.
        """
        logger.debug("Checking file %s", file)
        file_path = Path(file)
        if file_path.exists():
            if file_path.is_dir():
                raise IsADirectoryError(
                    f"Could not create file %s, there is a folder with the same name",
                    file,
                )
        else:
            try:
                file_path.parent.mkdir(exist_ok=True, parents=True)
                file_path.write_text(
                    "# robot-hat config and calibration value of robots\n\n"
                )
            except Exception as e:
                logger.error("Error creating file", exc_info=True)
                raise e

    def get(self, name: str, default_value: T) -> Union[T, str]:
        """
        Retrieves the value for a given key from the database file.

        If the key is missing, returns the provided default value instead.
        Skips malformed lines (those without an "=").

        Example:
            speed = db.get("speed", 50)  # Returns 50 if "speed" isn't present.
        """
        for line in self.parse_file():
            if "=" not in line:
                logger.warning("Skipping malformed line: '%s'", line)
                continue
            key, _, val = line.partition("=")
            if key.strip() == name:
                return val.replace(" ", "").strip()
        return default_value

    def parse_file(self) -> List[str]:
        """
        Reads and parses the database file, ignoring comments and blank lines.

        Returns a list of lines with the format "key = value". Lines that are
        empty or begin with "#" are excluded.
        """
        try:
            with open(self.db, "r") as conf:
                return [
                    line.strip() for line in conf if line.strip() and line[0] != "#"
                ]
        except FileNotFoundError:
            with open(self.db, "w") as conf:
                conf.write("")
            return []

    def set(self, name: str, value: str) -> None:
        """
        Sets or updates a key-value pair in the database file.

        If the key already exists, its value will be updated; otherwise, the
        key-value pair will be appended to the end of the file. If the file
        write operation fails, the original file remains unchanged because of
        the atomic file-writing mechanism.

        Raises a ValueError if the key is empty, contains "=", or the value
        contains newline characters.
        """
        if not name or "=" in name:
            raise ValueError(f"Invalid name: '{name}' cannot be empty or contain '='")
        if "\n" in value:
            raise ValueError("Value cannot contain newline characters")

        lines = []

        with open(self.db, "r") as conf:
            lines = conf.readlines()

        file_len = len(lines) - 1
        flag = False

        for i in range(file_len):
            if lines[i][0] != "#":
                if lines[i].split("=")[0].strip() == name:
                    lines[i] = f"{name} = {value}\n"
                    flag = True

        if not flag:
            lines.append(f"{name} = {value}\n")

        with open(f"{self.db}.tmp", "w") as tmp:
            tmp.writelines(lines)

        os.rename(f"{self.db}.tmp", self.db)

    def get_all_as_dict(self) -> Dict[str, str]:
        """
        Returns all key-value pairs from the database file as a dictionary.

        Keys and values are stripped of extraneous whitespace. Malformed lines
        are skipped, and comments are ignored.

        Example:
            config = db.get_all_as_dict()
            print(config)  # {'speed': '100', 'calibration': '1.23'}
        """
        data = {}
        for line in self.parse_file():
            key, _, val = line.partition("=")
            data[key.strip()] = val.replace(" ", "").strip()
        return data
