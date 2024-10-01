import logging.config

from app.config.log_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.paths import FRONTEND_FOLDER, STATIC_FOLDER, TEMPLATE_FOLDER
from app.util.get_ip_address import get_ip_address
from app.util.logger import Logger

Logger.setup_from_env()
logger = Logger(__name__)


description = """
`Picar-X Racer` is a project aimed at controlling the [Picar-X vehicle](https://docs.sunfounder.com/projects/picar-x/en/stable/) using a modern web interface inspired by racing video games.

This server runs in a separate process from the car-controlling server to ensure that control operations are never blocked.

It provides endpoints for:

- video streaming including AI object detection with YOLO and video enhancements,
- music/sound playback,
- managing settings and files,
- serving the frontend,
- reading battery status from ADC.
"""

tags_metadata = [
    {
        "name": "audio",
        "description": "Endpoints related to audio functionalities, including playing and managing music and sound effects.",
    },
    {
        "name": "battery",
        "description": "Endpoints related to battery status and monitoring, providing real-time insights into battery voltage levels.",
    },
    {
        "name": "camera",
        "description": "Endpoints for camera operations, including capturing photos and retrieving frame dimensions.",
    },
    {
        "name": "files",
        "description": "Endpoints for managing files, including uploading, listing, downloading, and deleting media files.",
    },
    {
        "name": "settings",
        "description": "Endpoints to retrieve and update various application settings, including calibration and video mode configuration.",
    },
    {
        "name": "video-stream",
        "description": "Endpoints for handling video feed settings and WebSocket connections for streaming real-time video.",
    },
    {
        "name": "serve",
        "description": "General serving endpoints, including serving the frontend application and handling fallback routes.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.template_folder = TEMPLATE_FOLDER
    port = app.state.port if hasattr(app.state, "port") else 8000

    ip_address = get_ip_address()
    BOLD = "\033[1m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    print(
        f"🚗 {BOLD}{RED}Open {YELLOW}http://{ip_address}:{port}{RED} in the browser{RESET}"
    )
    yield
    logger.info("Stopping application")


app = FastAPI(
    lifespan=lifespan,
    title="Picar X Racer",
    description=description,
    summary="Modern web interface for controlling the Picar-X vehicle with various features including video streaming, object detection, audio playback, and more.",
    version="0.0.1",
    contact={
        "name": "Karim Aziiev",
        "url": "http://github.com/KarimAziev/picar-x-racer",
        "email": "karim.aziiev@gmail.com",
    },
    license_info={
        "name": "GPL-3.0-or-later",
        "url": "https://www.gnu.org/licenses/gpl-3.0.en.html",
    },
    openapi_tags=tags_metadata,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")
app.mount("/frontend", StaticFiles(directory=FRONTEND_FOLDER), name="frontend")

from app.api.endpoints import (
    audio_management_router,
    battery_router,
    camera_feed_router,
    file_management_router,
    main_router,
    settings_router,
    video_feed_router,
)

app.include_router(audio_management_router, tags=["audio"])
app.include_router(battery_router, tags=["battery"])
app.include_router(camera_feed_router, tags=["camera"])
app.include_router(file_management_router, tags=["files"])
app.include_router(settings_router, tags=["settings"])
app.include_router(video_feed_router, tags=["video-stream"])
app.include_router(main_router, tags=["serve"])
