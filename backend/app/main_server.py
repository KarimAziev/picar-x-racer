"""
The application provides robot-agnostic functionality, including:
- Video streaming
- Managing settings and files
- Music/sound playback
- Serving the frontend
- Managing the operating system

The API responsible for robot hardware interactions runs in a separate
process to guarantee that control operations are never blocked.
"""

import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.config import settings
from app.core.logger import Logger
from app.util.ansi import print_initial_message
from app.util.get_ip_address import get_ip_address

if TYPE_CHECKING:
    from app.services.battery_service import BatteryService
    from app.services.camera_service import CameraService
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.music_service import MusicService


Logger.setup_from_env()

logger = Logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    app.state.cancelled = False
    connection_manager: Optional["ConnectionService"] = None
    battery_manager: Optional["BatteryService"] = None
    detection_manager: Optional["DetectionService"] = None
    music_manager: Optional["MusicService"] = None
    signal_file_path: Optional[str] = None
    camera_manager: Optional["CameraService"] = None

    try:
        from app.api import deps

        port = os.getenv("PX_MAIN_APP_PORT")
        mode = os.getenv("PX_APP_MODE")

        file_manager = deps.get_file_manager(audio_manager=deps.get_audio_manager())

        connection_manager = deps.get_connection_manager()
        app_manager = connection_manager
        battery_manager = deps.get_battery_manager(
            connection_manager=connection_manager,
            file_manager=file_manager,
        )
        detection_manager = deps.get_detection_manager(
            file_manager=file_manager, connection_manager=connection_manager
        )
        camera_manager = deps.get_camera_manager(
            detection_service=detection_manager,
            file_manager=file_manager,
            connection_manager=connection_manager,
            video_device_adapter=deps.get_video_device_adapter(),
            video_recorder=deps.get_video_recorder(),
        )
        music_manager = deps.get_music_manager(
            file_manager=file_manager, connection_manager=connection_manager
        )

        app.state.template_folder = settings.TEMPLATE_DIR
        app.state.app_manager = app_manager

        ip_address = get_ip_address()
        browser_url = f"http://{ip_address}:{port}"

        signal_file_path = "/tmp/backend_ready.signal" if mode == "dev" else None

        battery_manager.setup_connection_manager()
        music_manager.start_broadcast_task()

        if signal_file_path:
            try:
                with open(signal_file_path, "w") as f:
                    f.write("Backend is ready")
            except Exception as e:
                logger.error(f"Failed to create signal file: {e}")

        print_initial_message(browser_url)
        yield
    except asyncio.CancelledError:
        logger.warning(
            "Lifespan was cancelled mid-shutdown (first-level). Proceeding to final cleanup."
        )
    finally:
        app.state.cancelled = True
        if camera_manager:
            camera_manager.shutting_down = True
            await asyncio.to_thread(camera_manager.shutdown)

        logger.info(f"Stopping 🚗 {app.title} application")
        try:
            if battery_manager:
                await battery_manager.cleanup_connection_manager()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up battery_manager.")
            raise

        try:
            if music_manager:
                await music_manager.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up music_manager.")
            raise

        try:
            if detection_manager:
                await detection_manager.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up detection_manager.")
            raise

        if signal_file_path and os.path.exists(signal_file_path):
            os.remove(signal_file_path)

        logger.info(f"Application 🚗 {app.title} stopped")


from app.api.endpoints import api_router, serve_router, tags_metadata

app = FastAPI(
    lifespan=lifespan,
    title="Picar X Racer Core Application",
    summary="General-purpose APIs that are not directly related to the robot's hardware interactions.",
    description=__doc__ or "",
    version="0.0.1",
    contact={
        "name": "Karim Aziiev",
        "email": "karim.aziiev@gmail.com",
    },
    license_info={
        "name": "GNU General Public License v3.0 or later",
        "identifier": "GPL-3.0-or-later",
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


app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
app.mount("/frontend", StaticFiles(directory=settings.FRONTEND_DIR), name="frontend")

app.include_router(api_router, prefix="/api")
app.include_router(serve_router)
