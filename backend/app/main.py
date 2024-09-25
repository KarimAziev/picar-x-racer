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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.template_folder = TEMPLATE_FOLDER

    ip_address = get_ip_address()
    logger.info(
        f"\nTo access the frontend, open http://{ip_address}:8000 in the browser\n"
    )
    yield
    logger.info("Stopping application")


app = FastAPI(lifespan=lifespan, title="picar-x-racer-app")
logger = Logger(__name__)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")
app.mount("/frontend", StaticFiles(directory=FRONTEND_FOLDER), name="frontend")

from app.endpoints import (
    audio_management_router,
    battery_router,
    camera_feed_router,
    file_management_router,
    main_router,
    settings_router,
    video_feed_router,
)

app.include_router(audio_management_router)
app.include_router(battery_router)
app.include_router(camera_feed_router)
app.include_router(file_management_router)
app.include_router(settings_router)
app.include_router(video_feed_router)
app.include_router(main_router)
