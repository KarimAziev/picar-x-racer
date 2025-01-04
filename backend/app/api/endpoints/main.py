import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/", response_class=FileResponse)
def root(request: Request):
    """
    Serve the root HTML page of the frontend application.

    Returns:
    --------------
    **FileResponse**: The response containing the `index.html` file.

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


@router.get("/{path:path}")
def catch_all(request: Request, path: str):
    """
    Serve any requested file or fallback to the `index.html` for the frontend application.

    Returns:
    --------------
    **FileResponse**: The response containing the requested file or the `index.html` file.
    """
    template_folder = request.app.state.template_folder
    file_path = os.path.join(template_folder, path)

    if not os.path.isfile(file_path):
        file_path = os.path.join(template_folder, "index.html")

        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(file_path)
