"""
The application provides robot-agnostic functionality:
- Video streaming
- Managing settings and files
- Music/sound playback
- Serving the frontend
- Managing the operating system

The API responsible for robot hardware interactions runs in a separate
process to guarantee that control operations are never blocked.
"""

import os
import signal
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
    from app.services.connection_service import ConnectionService
    from app.services.detection.detection_service import DetectionService
    from app.services.media.music_file_service import MusicFileService


Logger.setup_from_env()

_log = Logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    app.state.cancelled = False
    signal_file_path: Optional[str] = None
    connection_manager: Optional["ConnectionService"] = None
    detection_manager: Optional["DetectionService"] = None
    music_file_service: Optional["MusicFileService"] = None

    def cancel_server(*_) -> None:
        _log.info(f"🛑 Received signal to stop {app.title}")
        app.state.cancelled = True

    try:
        signal.signal(signal.SIGINT, cancel_server)
        from app.api import deps
        from app.util.solve_lifespan import solve_lifespan

        port = os.getenv("PX_MAIN_APP_PORT")
        mode = os.getenv("PX_APP_MODE")

        lifespan_deps = solve_lifespan(deps.get_lifespan_dependencies)
        async with lifespan_deps(app) as deps:
            connection_manager = deps.get("connection_manager")
            detection_manager = deps.get("detection_manager")
            music_file_service = deps.get("music_file_service")

        app.state.template_folder = settings.TEMPLATE_DIR
        app.state.app_manager = connection_manager

        ip_address = get_ip_address()
        browser_url = f"http://{ip_address}:{port}"

        signal_file_path = "/tmp/backend_ready.signal" if mode == "dev" else None

        sorted_tracks = music_file_service.list_sorted_tracks()

        music_file_service.music_service.update_tracks(sorted_tracks)
        music_file_service.music_service.start_broadcast_task()

        if signal_file_path:
            try:
                with open(signal_file_path, "w") as f:
                    f.write("Backend is ready")
            except Exception as e:
                _log.error(f"Failed to create signal file: {e}")

        print_initial_message(browser_url)
        yield
    except asyncio.CancelledError:
        _log.warning(
            "Lifespan was cancelled mid-shutdown (first-level). Proceeding to final cleanup."
        )
    finally:
        app.state.cancelled = True

        _log.info(f"Stopping {app.title}")
        try:
            if music_file_service:
                await music_file_service.music_service.cleanup()
        except asyncio.CancelledError:
            _log.warning("Cancelled while cleaning up music_file_service.")
            raise

        try:
            if detection_manager:
                await detection_manager.cleanup()
        except asyncio.CancelledError:
            _log.warning("Cancelled while cleaning up detection_manager.")
            raise

        if signal_file_path and os.path.exists(signal_file_path):
            os.remove(signal_file_path)

        _log.info(f"{app.title} stopped")


from app.api.endpoints import api_router, serve_router, tags_metadata

app = FastAPI(
    lifespan=lifespan,
    title="Picar X Racer Core Application",
    summary="General-purpose APIs that are not directly related to the robot's hardware interactions.",
    description=__doc__ or "",
    version="1.0.0",
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
