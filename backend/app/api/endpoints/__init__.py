import app.api.endpoints.app_syncer as syncer
import app.api.endpoints.audio as audio
import app.api.endpoints.camera as camera
import app.api.endpoints.default as serve
import app.api.endpoints.detection as detection
import app.api.endpoints.file_management as file_management
import app.api.endpoints.music as music
import app.api.endpoints.settings as settings
import app.api.endpoints.system as system
import app.api.endpoints.tts as tts
import app.api.endpoints.video_feed as video_feed
from app.util.endpoints_metadata import build_routers_and_metadata, process_module_route
from fastapi import APIRouter

api_router = APIRouter()

routers, tags_metadata = build_routers_and_metadata(
    [
        camera,
        detection,
        video_feed,
        file_management,
        settings,
        audio,
        tts,
        music,
        system,
        syncer,
    ]
)

serve_router, serve_metadata = process_module_route(serve)

tags_metadata.append(serve_metadata)


for router in routers:
    api_router.include_router(router, tags=router.tags)


__all__ = [
    "serve_router",
    "api_router",
    "tags_metadata",
]
