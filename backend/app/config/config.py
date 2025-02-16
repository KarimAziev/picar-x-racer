from os import path
from typing import Literal, Optional

from platformdirs import (
    user_cache_dir,
    user_config_dir,
    user_music_dir,
    user_pictures_dir,
    user_videos_dir,
)
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated

_PROJECT_DIR: str = path.dirname(
    path.dirname(path.dirname(path.dirname(path.realpath(__file__))))
)
_FRONTED_APP_DIR = path.join(_PROJECT_DIR, "frontend")
_TEMPLATE_DIR = path.join(_FRONTED_APP_DIR, "dist")
_STATIC_DIR = path.join(_FRONTED_APP_DIR, _TEMPLATE_DIR, "assets")

_USER_CONFIG_DIR = user_config_dir()

env_file = path.join(
    _PROJECT_DIR,
    "backend",
    ".env",
)


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file,
        extra="ignore",
        case_sensitive=True,
    )
    APP_NAME: str = "picar-x-racer"

    PX_PHOTO_DIR: Annotated[
        str, Field(..., description="The directory to save captured photos.")
    ] = path.join(user_pictures_dir(), APP_NAME)

    PX_VIDEO_DIR: Annotated[
        str, Field(..., description="The directory to save recorded videos.")
    ] = path.join(user_videos_dir(), APP_NAME)

    PX_MUSIC_DIR: Annotated[
        str, Field(..., description="The directory to store uploaded music.")
    ] = path.join(user_music_dir(), APP_NAME, "music")

    MUSIC_CACHE_FILE_PATH: Annotated[
        str, Field(..., description="The location to write music cache metadata.")
    ] = path.join(user_cache_dir(), APP_NAME, "music_cache.json")

    VIDEO_CACHE_FILE_PATH: Annotated[
        str, Field(..., description="The location to write video cache metadata.")
    ] = path.join(user_cache_dir(), APP_NAME, "video_cache.json")

    VIDEO_CACHE_PREVIEW_DIR: Annotated[
        str, Field(..., description="The directory to save preview images for videos.")
    ] = path.join(user_cache_dir(), APP_NAME, "video_preview")

    PX_SETTINGS_FILE: Annotated[
        str, Field(..., description="The location to write user settings.")
    ] = path.join(_USER_CONFIG_DIR, APP_NAME, "user_settings.json")

    ROBOT_CONFIG_FILE: Annotated[
        str,
        Field(
            ...,
            description="The file containing calibration and robot hardware settings.",
        ),
    ] = path.join(_USER_CONFIG_DIR, APP_NAME, "config.json")

    DEFAULT_ROBOT_CONFIG_FILE: Annotated[
        str,
        Field(..., description="The default robot configuration template."),
    ] = path.join(_PROJECT_DIR, "config.json")

    DATA_DIR: Annotated[
        str,
        Field(
            ...,
            description="The directory containing object detection models. "
            "Loadable models will be saved in this directory.",
        ),
    ] = path.join(_PROJECT_DIR, "data")

    DEFAULT_USER_SETTINGS: Annotated[
        str,
        Field(..., description="The default user settings template."),
    ] = path.join(_PROJECT_DIR, "user_settings.json")

    DEFAULT_MUSIC_DIR: Annotated[
        str,
        Field(
            ...,
            description="The directory containing default music. "
            "This music cannot be removed by users.",
        ),
    ] = path.join(_PROJECT_DIR, "music")

    DEFAULT_SOUNDS_DIR: Annotated[
        str,
        Field(
            ...,
            description="The directory containing default app sounds. "
            "These sounds cannot be removed by users.",
        ),
    ] = path.join(_PROJECT_DIR, "sounds")

    FRONTEND_DIR: Annotated[
        str,
        Field(
            ..., description="The directory containing the frontend application files."
        ),
    ] = _FRONTED_APP_DIR

    STATIC_DIR: Annotated[
        str,
        Field(
            ...,
            description="The directory containing static assets for the frontend application.",
        ),
    ] = _STATIC_DIR

    TEMPLATE_DIR: Annotated[
        str,
        Field(
            _TEMPLATE_DIR,
            description="The directory containing the root HTML page (index.html) of the frontend application.",
        ),
    ] = _TEMPLATE_DIR

    FONT_PATH: str = path.join(
        _PROJECT_DIR, "frontend/src/assets/font/tt-octosquares-regular.ttf"
    )

    YOLO_MODEL_PATH: Annotated[
        str,
        Field(
            ..., description="The default YOLO model to use in the export_model script."
        ),
    ] = path.join(_PROJECT_DIR, "data", "yolov8n.pt")

    YOLO_MODEL_EDGE_TPU_PATH: Annotated[
        str,
        Field(
            ...,
            description="The default Edge TPU TFLite model to use in the export_model script.",
        ),
    ] = path.join(_PROJECT_DIR, "data", "yolov8n_320_edgetpu.tflite")

    PX_LOG_LEVEL: Annotated[
        Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        Field(
            ...,
            description="The log level for the application. Determines the severity of messages to be logged.",
        ),
    ] = "INFO"

    PX_LOG_DIR: Annotated[
        Optional[str],
        Field(
            None,
            description="The directory for logging. If provided, logs will be written to separate "
            "'app.log' and 'error.log' files. Messages at WARNING level or higher will also "
            "be output to stdout.",
        ),
    ] = None

    PX_MAIN_APP_PORT: Annotated[
        int, Field(8000, description="The port to run the main server on.")
    ] = 8000

    PX_CONTROL_APP_PORT: Annotated[
        int, Field(8001, description="The port to run the control server on.")
    ] = 8001

    ROBOT_HAT_MOCK_SMBUS: Annotated[
        Optional[Literal["1"]],
        Field(
            None,
            description="If set, a mocked smbus2 implementation will be used. "
            "This may be useful for development on non-Raspberry systems.",
        ),
    ] = None

    ROBOT_HAT_DISCHARGE_RATE: Annotated[
        Optional[int],
        Field(
            ...,
            ge=1,
            description="The step size for mocked battery discharging. A higher value indicates faster discharge. "
            "This setting is used only in conjunction with `ROBOT_HAT_MOCK_SMBUS`.",
            examples=[10],
        ),
    ] = 20

    HAILO_LABELS: Annotated[
        Optional[str],
        Field(
            ...,
            description="Path to a text file containing labels. If no labels file is provided, coco2017 will be used. ",
        ),
    ] = path.join(_PROJECT_DIR, "coco2017.txt")


settings = AppConfig()
