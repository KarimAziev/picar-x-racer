from .app_syncer import router as app_sync_router
from .audio import router as audio_management_router
from .battery import router as battery_router
from .camera import router as camera_feed_router
from .detection import router as detection_router
from .file_management import router as file_management_router
from .main import router as main_router
from .music import router as music_router
from .settings import router as settings_router
from .tts import router as tts_router
from .video_feed import router as video_feed_router

__all__ = [
    "video_feed_router",
    "app_sync_router",
    "audio_management_router",
    "battery_router",
    "camera_feed_router",
    "detection_router",
    "file_management_router",
    "main_router",
    "music_router",
    "settings_router",
    "tts_router",
]
