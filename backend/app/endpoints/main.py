import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

main_router = APIRouter()


@main_router.get("/", response_class=FileResponse)
def root(request: Request):
    template_folder = request.app.state.template_folder

    if not isinstance(template_folder, str) or not os.path.isdir(template_folder):
        raise ValueError("Template folder is not a valid path.")

    file_path = os.path.join(template_folder, "index.html")

    if not os.path.isfile(file_path):
        raise FileNotFoundError("index.html not found in the template folder.")

    return file_path


@main_router.get("/{path:path}")
def catch_all(request: Request, path: str):
    template_folder = request.app.state.template_folder
    file_path = os.path.join(template_folder, path)

    if not os.path.isfile(file_path):
        file_path = os.path.join(template_folder, "index.html")

    return FileResponse(file_path)
