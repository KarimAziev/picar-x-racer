import logging.config
import os

from app.config.log_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.paths import FRONTEND_FOLDER, STATIC_FOLDER, TEMPLATE_FOLDER
from app.util.ansi import print_initial_message
from app.util.get_ip_address import get_ip_address
from app.util.logger import Logger

if TYPE_CHECKING:
    from app.services.battery_service import BatteryService
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.music_service import MusicService


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
- managing the operating system.
"""

tags_metadata = [
    {
        "name": "sync",
        "description": "Websocket endpoint for synchronizing app state between several clients",
    },
    {
        "name": "audio",
        "description": "Endpoints related to audio functionalities, including volume controls.",
    },
    {
        "name": "tts",
        "description": "Endpoints related to text to speech functionalities.",
    },
    {
        "name": "music",
        "description": "Endpoints related to music playing.",
    },
    {
        "name": "battery",
        "description": "Endpoints related to battery status and monitoring.",
    },
    {
        "name": "camera",
        "description": "Endpoints for camera operations, including capturing photos.",
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
        "name": "detection",
        "description": "Endpoints for handling object detection.",
    },
    {
        "name": "serve",
        "description": "General serving endpoints, including serving the frontend application and handling fallback routes.",
    },
    {
        "name": "system",
        "description": (
            "Operations and endpoints related to system-level actions. These include "
            "managing the operating system, such as shutting down."
            "Use these endpoints with caution as they interact directly with the underlying OS."
        ),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.api import deps

    file_manager = deps.get_file_manager(audio_manager=deps.get_audio_manager())

    connection_manager: "ConnectionService" = deps.get_connection_manager()
    app_manager = connection_manager
    battery_manager: "BatteryService" = deps.get_battery_manager(
        connection_manager=connection_manager,
        file_manager=file_manager,
    )
    detection_manager: "DetectionService" = deps.get_detection_manager(
        file_manager=file_manager, connection_manager=connection_manager
    )
    music_manager: "MusicService" = deps.get_music_manager(
        file_manager=file_manager, connection_manager=connection_manager
    )

    app.state.template_folder = TEMPLATE_FOLDER
    app.state.app_manager = app_manager
    port = os.getenv("PX_MAIN_APP_PORT")
    mode = os.getenv("PX_APP_MODE")

    ip_address = get_ip_address()
    browser_url = f"http://{ip_address}:{port}"

    print_initial_message(browser_url)

    signal_file_path = '/tmp/backend_ready.signal' if mode == "dev" else None

    battery_manager.setup_connection_manager()
    music_manager.start_broadcast_task()

    if signal_file_path:
        try:
            with open(signal_file_path, 'w') as f:
                f.write('Backend is ready')
        except Exception as e:
            logger.error(f"Failed to create signal file: {e}")

    try:
        yield
    finally:
        logger.info("Stopping 🚗 application")
        await battery_manager.cleanup_connection_manager()
        await detection_manager.cleanup()
        await music_manager.cleanup()
        if signal_file_path and os.path.exists(signal_file_path):
            os.remove(signal_file_path)
        logger.info("Application 🚗 stopped")


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
    app_sync_router,
    audio_management_router,
    battery_router,
    camera_feed_router,
    detection_router,
    file_management_router,
    main_router,
    music_router,
    settings_router,
    system_router,
    tts_router,
    video_feed_router,
)

app.include_router(audio_management_router, tags=["audio"])
app.include_router(music_router, tags=["music"])
app.include_router(tts_router, tags=["tts"])
app.include_router(battery_router, tags=["battery"])
app.include_router(camera_feed_router, tags=["camera"])
app.include_router(file_management_router, tags=["files"])
app.include_router(settings_router, tags=["settings"])
app.include_router(video_feed_router, tags=["video-stream"])
app.include_router(detection_router, tags=["detection"])
app.include_router(app_sync_router, tags=["sync"])
app.include_router(system_router, tags=["system"])
app.include_router(main_router, tags=["serve"])
