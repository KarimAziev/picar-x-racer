from functools import lru_cache
from typing import Annotated, AsyncGenerator, TypedDict

from app.adapters.picarx_adapter import PicarxAdapter
from app.config.config import settings as app_config
from app.core.async_emitter import AsyncEventEmitter
from app.core.logger import Logger
from app.managers.async_task_manager import AsyncTaskManager
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.battery import BatterySettings
from app.services.connection_service import ConnectionService
from app.services.control.calibration_service import CalibrationService
from app.services.control.car_service import CarService
from app.services.sensors.battery_service import BatteryService
from app.services.sensors.distance_service import DistanceService
from app.services.sensors.led_service import LEDService
from fastapi import Depends
from robot_hat.battery import Battery

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


def get_distance_service(
    emitter: AsyncEventEmitter = Depends(get_async_event_emitter),
    task_manager: AsyncTaskManager = Depends(get_async_task_manager),
) -> DistanceService:
    return DistanceService(
        emitter=emitter,
        task_manager=task_manager,
    )


@lru_cache()
def get_led_service(
    emitter: AsyncEventEmitter = Depends(get_async_event_emitter),
    task_manager: AsyncTaskManager = Depends(get_async_task_manager),
    config_manager: JsonDataManager = Depends(get_config_manager),
) -> LEDService:
    return LEDService(
        config_manager=config_manager, emitter=emitter, task_manager=task_manager
    )


@lru_cache()
def get_battery_adapter() -> Battery:
    return Battery()


@lru_cache()
def get_battery_service(
    connection_manager: Annotated[ConnectionService, Depends(get_connection_manager)],
    settings_service: Annotated[JsonDataManager, Depends(get_app_settings_manager)],
    battery_adapter: Annotated[Battery, Depends(get_battery_adapter)],
) -> BatteryService:
    app_settings = settings_service.load_data()
    battery_settings = BatterySettings(
        **app_settings.get(
            "battery",
            {
                "full_voltage": 8.4,
                "warn_voltage": 7.15,
                "danger_voltage": 6.5,
                "min_voltage": 6.0,
                "auto_measure_seconds": 60,
                "cache_seconds": 2,
            },
        )
    )
    return BatteryService(
        connection_manager=connection_manager,
        settings=battery_settings,
        battery_adapter=battery_adapter,
    )


def get_picarx_adapter(
    config_manager: JsonDataManager = Depends(get_config_manager),
) -> PicarxAdapter:
    return PicarxAdapter(config_manager=config_manager)


def get_calibration_service(
    px: PicarxAdapter = Depends(get_picarx_adapter),
    config_manager: JsonDataManager = Depends(get_config_manager),
) -> CalibrationService:
    return CalibrationService(px, config_manager=config_manager)


def get_robot_service(
    connection_manager: ConnectionService = Depends(get_connection_manager),
    picarx_adapter: PicarxAdapter = Depends(get_picarx_adapter),
    calibration_service: CalibrationService = Depends(get_calibration_service),
    distance_service: DistanceService = Depends(get_distance_service),
    app_settings_manager: JsonDataManager = Depends(get_app_settings_manager),
    config_manager: JsonDataManager = Depends(get_config_manager),
    led_service: LEDService = Depends(get_led_service),
) -> CarService:
    return CarService(
        connection_manager=connection_manager,
        px=picarx_adapter,
        calibration_service=calibration_service,
        distance_service=distance_service,
        app_settings_manager=app_settings_manager,
        config_manager=config_manager,
        led_service=led_service,
    )


class LifespanAppDeps(TypedDict):
    connection_service: ConnectionService
    battery_service: BatteryService
    robot_service: CarService
    settings_service: JsonDataManager
    distance_service: DistanceService
    led_service: LEDService


async def get_lifespan_dependencies(
    connection_service: Annotated[ConnectionService, Depends(get_connection_manager)],
    battery_service: Annotated[BatteryService, Depends(get_battery_service)],
    robot_service: Annotated[CarService, Depends(get_robot_service)],
    settings_service: Annotated[JsonDataManager, Depends(get_app_settings_manager)],
    distance_service: Annotated[DistanceService, Depends(get_distance_service)],
    led_service: Annotated[LEDService, Depends(get_led_service)],
) -> AsyncGenerator[LifespanAppDeps, None]:
    deps: LifespanAppDeps = {
        "connection_service": connection_service,
        "battery_service": battery_service,
        "robot_service": robot_service,
        "distance_service": distance_service,
        "settings_service": settings_service,
        "led_service": led_service,
    }
    yield deps
