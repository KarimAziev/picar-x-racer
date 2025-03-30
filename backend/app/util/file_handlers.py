from typing import Dict, Tuple, Union

from app.schemas.file_management import AliasDir
from app.services.file_management.file_manager_service import FileManagerService
from app.util.file_util import file_in_directory


def find_file_handler(
    file: str, handlers: Dict[AliasDir, FileManagerService]
) -> Union[Tuple[AliasDir, FileManagerService], Tuple[None, None]]:

    for alias, handler in handlers.items():
        if file_in_directory(
            file,
            handler.root_directory,
        ):
            return (alias, handler)

    return (None, None)
