import json
import os
from enum import Enum
from typing import Any, Dict

from app.core.event_emitter import EventEmitter
from app.core.logger import Logger
from app.util.atomic_write import atomic_write
from app.util.file_util import load_json_file


class JsonDataManagerEvent(Enum):
    """Enumeration of json data manager events."""

    UPDATE = "update"
    LOAD = "load"


class JsonDataManager(EventEmitter):
    """
    A lightweight, file-backed JSON data manager with caching, atomic save, and
    event-driven functionality.

    - Supports loading from a primary target file or a fallback template file.
    - Transparent file caching to optimize repeated reads.
    - Atomic saves to ensure file integrity.
    - Event-driven updates using the EventEmitter system.

    Usage Example:
    ```python
    from app.managers.json_data_manager import JsonDataManager

    # Initialize the manager
    json_manager = JsonDataManager("path/to/target.json", "path/to/template.json")


    # Subscribe to update events
    def on_update(new_data):
        print(f"Data updated: {new_data}")


    json_manager.on(JsonDataManagerEvent.UPDATE_EVENT, on_update)

    # Load data
    data = json_manager.load_data()

    # Update whole data
    json_manager.update({"key": "value"})  # emitted

    # Merge new data into existing JSON
    json_manager.merge({"new_key": "new_value"})  # emitted

    ```
    """

    UPDATE_EVENT = JsonDataManagerEvent.UPDATE.value
    LOAD_EVENT = JsonDataManagerEvent.LOAD.value

    def __init__(self, target_file: str, template_file: str, *args, **kwargs):
        """
        Initialize the JSON data manager.

        Args:
            target_file: The path to the primary target file.
            template_file: The path to the fallback template file, used if the target file doesn't exist.
        """
        super().__init__(*args, **kwargs)
        self._logger = Logger(name=__name__)
        self._target_file = target_file
        self._template_file = template_file
        self._last_modified_time = None
        self._last_cached_file = None
        self._cache: Dict[str, Any] = self.load_data()

    @property
    def source_file(self):
        """
        Determine the current source file being used.

        Returns:
            The path to the target file if it exists; otherwise, the path to the template file.
        """
        return (
            self._target_file
            if os.path.exists(self._target_file)
            else self._template_file
        )

    def load_data(self) -> Dict[str, Any]:
        """
        Load the current JSON data, either from the cache or the appropriate source file.

        Returns:
            The JSON data loaded from the file as a dictionary.
        """
        source_file = self.source_file

        try:
            modified_time = os.path.getmtime(source_file)
        except OSError:
            modified_time = None

        if (
            not hasattr(self, "_cache")
            or self._cache is None
            or self._last_modified_time != modified_time
            or self._last_cached_file != source_file
        ):
            self._logger.info(f"Loading data from {source_file}")
            self._cache: Dict[str, Any] = load_json_file(source_file)
            self._last_modified_time = modified_time
            self._last_cached_file = source_file
            self.emit(self.LOAD_EVENT, self._cache)
        else:
            self._logger.debug(f"Using cache for {self._last_cached_file}")

        return self._cache

    def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the file with new JSON data.

        Args:
            data: A dictionary representing the new JSON data to save.

        Returns:
            The updated JSON data.
        """
        self._logger.info("Saving '%s'", self._target_file)
        with atomic_write(self._target_file) as tmp:
            json.dump(data, tmp, indent=2)
        self._cache = data
        self._logger.info("File '%s' sucessfully saved", self._target_file)
        self.emit(self.UPDATE_EVENT, self._cache)
        return self._cache

    def merge(self, partial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge new key-value pairs into the existing JSON data.

        Args:
            partial_data: A dictionary containing the key-value pairs to merge into the existing data.

        Returns:
            The merged JSON data after saving.
        """
        self._logger.debug("Merging partial data %s", partial_data)
        existing_data = self.load_data()
        merged_data = {
            **existing_data,
            **partial_data,
        }
        return self.update(merged_data)
