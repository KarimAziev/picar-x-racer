"""
General serving endpoints, including serving the frontend application and handling fallback routes.
"""

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()


@router.get(
    "/",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Successfully served the `index.html` file.",
            "content": {
                "text/html": {
                    "example": "<!doctype html>"
                    "<html lang=\"en\" class=\"p-dark\">"
                    "  <head>"
                    "    <meta"
                    "      charset=\"UTF-8\""
                    "      content=\"width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover\""
                    "    />"
                    "    <link rel=\"icon\" type=\"image/svg+xml\" href=\"/logo.svg\" />"
                    "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />"
                    "    <title>Picar X Racer</title>"
                    "    <script type=\"module\" crossorigin src=\"/assets/index-CrzouHxf.js\"></script>"
                    "    <link rel=\"stylesheet\" crossorigin href=\"/assets/index-JaVzmKHq.css\">"
                    "  </head>"
                    "  <body>"
                    "    <div id=\"app\"></div>"
                    "  </body>"
                    "</html>"
                }
            },
        },
        400: {
            "description": "Bad Request: Template folder path is invalid.",
            "content": {
                "application/json": {
                    "example": {"detail": "Template folder is not a valid path."}
                }
            },
        },
        404: {
            "description": "`index.html` file not found in the template folder.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "index.html not found in the template folder."
                    },
                }
            },
        },
    },
)
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


@router.get(
    "/{path:path}",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Successfully served the requested file or `index.html` fallback.",
        },
        404: {
            "description": "File not found in the template folder.",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found."},
                }
            },
        },
    },
)
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
