"""
General serving endpoints, including serving the frontend application and handling fallback routes.
"""

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()

no_cache_headers = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


@router.get(
    "/",
    response_class=FileResponse,
    response_description="The response containing the `index.html` file",
    responses={
        200: {
            "description": "Successfully served the `index.html` file.",
            "content": {
                "text/html": {
                    "example": "<!doctype html>"
                    '<html lang="en" class="p-dark">'
                    "<head>"
                    '<meta charset="UTF-8" '
                    'content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover"'
                    " />"
                    '<link rel="icon" type="image/svg+xml" href="/logo.svg" />'
                    '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
                    "<title>Picar X Racer</title>"
                    '<script type="module" crossorigin src="/assets/index-CrzouHxf.js"></script>'
                    '<link rel="stylesheet" crossorigin href="/assets/index-JaVzmKHq.css">'
                    "</head>"
                    "<body>"
                    '<div id="app"></div>'
                    "</body>"
                    "</html>"
                }
            },
        },
        503: {
            "description": "Service Unavailable. Template folder is not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Template directory is unavailable."}
                }
            },
        },
        404: {
            "description": "`index.html` file not found in the template folder.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "File not found.",
                    },
                }
            },
        },
    },
)
def root(request: Request):
    """
    Serve the root HTML page of the frontend application.

    """
    template_folder: str = request.app.state.template_folder

    if not os.path.isdir(template_folder):
        raise HTTPException(
            status_code=503, detail="Template directory is unavailable."
        )

    file_path = os.path.join(template_folder, "index.html")

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(file_path, headers=no_cache_headers)


@router.get(
    "/{path:path}",
    response_class=FileResponse,
    response_description="The response containing the requested file or the `index.html` file",
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
    """
    template_folder = request.app.state.template_folder
    file_path = os.path.join(template_folder, path)

    if not os.path.isfile(file_path):
        file_path = os.path.join(template_folder, "index.html")

        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(file_path, headers=no_cache_headers)
