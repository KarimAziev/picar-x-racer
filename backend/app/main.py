from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.paths import FRONTEND_FOLDER, STATIC_FOLDER, TEMPLATE_FOLDER
from app.endpoints import (
    audio_management_router,
    battery_router,
    camera_feed_router,
    car_controller_router,
    distance_router,
    file_management_router,
    main_router,
    settings_router,
    video_feed_router,
)
from app.util.get_ip_address import get_ip_address
from app.util.logger import Logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    ip_address = get_ip_address()

    app.state.template_folder = TEMPLATE_FOLDER
    logger.info(
        f"\nTo access the frontend, open your browser and navigate to http://{ip_address}:9000\n"
    )
    yield


app = FastAPI(lifespan=lifespan, title="picar-x-racer")
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


app.include_router(audio_management_router)
app.include_router(battery_router)
app.include_router(camera_feed_router)
app.include_router(car_controller_router)
app.include_router(distance_router)
app.include_router(file_management_router)
app.include_router(settings_router)
app.include_router(video_feed_router)
app.include_router(main_router)
