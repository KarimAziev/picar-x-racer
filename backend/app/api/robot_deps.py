from functools import lru_cache
from typing import Annotated, AsyncGenerator, TypedDict

from app.adapters.picarx_adapter import PicarxAdapter
from app.config.config import settings as app_config
from app.core.async_emitter import AsyncEventEmitter
from app.core.logger import Logger
from app.managers.async_task_manager import AsyncTaskManager
from app.managers.file_management.json_data_manager import JsonDataManager
from app.services.connection_service import ConnectionService
from app.services.control.calibration_service import CalibrationService
from app.services.control.car_service import CarService
from app.services.sensors.battery_service import BatteryService
from app.services.sensors.distance_service import DistanceService
from app.services.sensors.led_service import LEDService
from app.services.sensors.speed_estimator import SpeedEstimator
from fastapi import Depends
from robot_hat.i2c.smbus_manager import SMBusManager

logger = Logger(__name__)


@lru_cache()
def get_connection_manager() -> ConnectionService:
    """Return connection manager used for broadcasting."""
    return ConnectionService(app_name="px_robot")


@lru_cache()
def get_async_event_emitter() -> AsyncEventEmitter:
    return AsyncEventEmitter()


@lru_cache()
def get_async_task_manager() -> AsyncTaskManager:
    return AsyncTaskManager()


@lru_cache()
def get_config_manager() -> JsonDataManager:
    return JsonDataManager(
        target_file=app_config.ROBOT_CONFIG_FILE,
        template_file=app_config.DEFAULT_ROBOT_CONFIG_FILE,
    )


@lru_cache()
def get_app_settings_manager() -> JsonDataManager:
    return JsonDataManager(
        target_file=app_config.PX_SETTINGS_FILE,
        template_file=app_config.DEFAULT_USER_SETTINGS,
    )


@lru_cache()
def get_speed_estimator() -> SpeedEstimator:
    return SpeedEstimator()


def get_distance_service(
    emitter: Annotated[AsyncEventEmitter, Depends(get_async_event_emitter)],
    task_manager: Annotated[AsyncTaskManager, Depends(get_async_task_manager)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
) -> DistanceService:
    return DistanceService(
        emitter=emitter, task_manager=task_manager, config_manager=config_manager
    )


@lru_cache()
def get_led_service(
    emitter: Annotated[AsyncEventEmitter, Depends(get_async_event_emitter)],
    task_manager: Annotated[AsyncTaskManager, Depends(get_async_task_manager)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
) -> LEDService:
    return LEDService(
        config_manager=config_manager, emitter=emitter, task_manager=task_manager
    )


@lru_cache()
def get_smbus_manager() -> SMBusManager:
    return SMBusManager()


@lru_cache()
def get_battery_service(
    connection_manager: Annotated[ConnectionService, Depends(get_connection_manager)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    smbus_manager: Annotated[SMBusManager, Depends(get_smbus_manager)],
) -> BatteryService:
    return BatteryService(
        connection_manager=connection_manager,
        config_manager=config_manager,
        smbus_manager=smbus_manager,
    )


def get_picarx_adapter(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    smbus_manager: Annotated[SMBusManager, Depends(get_smbus_manager)],
) -> PicarxAdapter:
    return PicarxAdapter(config_manager=config_manager, smbus_manager=smbus_manager)


def get_calibration_service(
    px: Annotated[PicarxAdapter, Depends(get_picarx_adapter)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
) -> CalibrationService:
    return CalibrationService(px, config_manager=config_manager)


def get_robot_service(
    connection_manager: Annotated[ConnectionService, Depends(get_connection_manager)],
    picarx_adapter: Annotated[PicarxAdapter, Depends(get_picarx_adapter)],
    calibration_service: Annotated[
        CalibrationService, Depends(get_calibration_service)
    ],
    distance_service: Annotated[DistanceService, Depends(get_distance_service)],
    app_settings_manager: Annotated[JsonDataManager, Depends(get_app_settings_manager)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    led_service: Annotated[LEDService, Depends(get_led_service)],
    speed_estimator: Annotated[SpeedEstimator, Depends(get_speed_estimator)],
) -> CarService:
    return CarService(
        connection_manager=connection_manager,
        px=picarx_adapter,
        calibration_service=calibration_service,
        distance_service=distance_service,
        app_settings_manager=app_settings_manager,
        config_manager=config_manager,
        led_service=led_service,
        speed_estimator=speed_estimator,
    )


class LifespanAppDeps(TypedDict):
    connection_service: ConnectionService
    battery_service: BatteryService
    robot_service: CarService
    settings_service: JsonDataManager
    distance_service: DistanceService
    led_service: LEDService
    speed_estimator: SpeedEstimator


async def get_lifespan_dependencies(
    connection_service: Annotated[ConnectionService, Depends(get_connection_manager)],
    battery_service: Annotated[BatteryService, Depends(get_battery_service)],
    robot_service: Annotated[CarService, Depends(get_robot_service)],
    settings_service: Annotated[JsonDataManager, Depends(get_app_settings_manager)],
    distance_service: Annotated[DistanceService, Depends(get_distance_service)],
    led_service: Annotated[LEDService, Depends(get_led_service)],
    speed_estimator: Annotated[SpeedEstimator, Depends(get_speed_estimator)],
) -> AsyncGenerator[LifespanAppDeps, None]:
    deps: LifespanAppDeps = {
        "connection_service": connection_service,
        "battery_service": battery_service,
        "robot_service": robot_service,
        "distance_service": distance_service,
        "settings_service": settings_service,
        "led_service": led_service,
        "speed_estimator": speed_estimator,
    }
    yield deps
