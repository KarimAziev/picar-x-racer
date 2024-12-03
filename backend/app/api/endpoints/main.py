import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

main_router = APIRouter()


@main_router.get("/", response_class=FileResponse)
def root(request: Request):
    """
    Serve the root HTML page of the frontend application.

    Args:
    --------------
    - request (Request): The incoming request object.

    Returns:
    --------------
    FileResponse: The response containing the `index.html` file.

    Raises:
    --------------
    - ValueError: If the template folder path is invalid.
    - FileNotFoundError: If the `index.html` file is not found in the template folder.
    """
    template_folder = request.app.state.template_folder

    if not isinstance(template_folder, str) or not os.path.isdir(template_folder):
        raise ValueError("Template folder is not a valid path.")

    file_path = os.path.join(template_folder, "index.html")

    if not os.path.isfile(file_path):
        raise FileNotFoundError("index.html not found in the template folder.")

    return file_path


@main_router.get("/{path:path}")
def catch_all(request: Request, path: str):
    """
    Serve any requested file or fallback to the `index.html` for the frontend application.

    Args:
    --------------
    - request (Request): The incoming request object.
    - path (str): The path of the requested file.

    Returns:
    --------------
    `FileResponse`: The response containing the requested file or the `index.html` file.

    Raises:
    --------------

    HTTPException (404): If the requested file or `index.html` is not found.
    """
    template_folder = request.app.state.template_folder
    file_path = os.path.join(template_folder, path)

    if not os.path.isfile(file_path):
        file_path = os.path.join(template_folder, "index.html")

        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(file_path)
