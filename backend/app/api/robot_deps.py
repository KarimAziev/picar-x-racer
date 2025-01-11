from functools import lru_cache

from app.adapters.picarx_adapter import PicarxAdapter
from app.core.async_emitter import AsyncEventEmitter
from app.core.logger import Logger
from app.managers.async_task_manager import AsyncTaskManager
from app.services.car_control.calibration_service import CalibrationService
from app.services.car_control.car_service import CarService
from app.services.car_control.config_service import ConfigService
from app.services.connection_service import ConnectionService
from app.services.distance_service import DistanceService
from fastapi import Depends

logger = Logger(__name__)


@lru_cache()
def get_connection_manager() -> ConnectionService:
    return ConnectionService(app_name="px_robot")


@lru_cache()
def get_async_event_emitter() -> AsyncEventEmitter:
    return AsyncEventEmitter()


@lru_cache()
def get_async_task_manager() -> AsyncTaskManager:
    return AsyncTaskManager()


def get_config_manager() -> ConfigService:

    return ConfigService()


def get_distance_service(
    emitter: AsyncEventEmitter = Depends(get_async_event_emitter),
    task_manager: AsyncTaskManager = Depends(get_async_task_manager),
) -> DistanceService:
    return DistanceService(
        emitter=emitter,
        task_manager=task_manager,
    )


def get_picarx_adapter(
    config_manager: ConfigService = Depends(get_config_manager),
) -> PicarxAdapter:
    return PicarxAdapter(config_manager=config_manager)


def get_calibration_service(
    px: PicarxAdapter = Depends(get_picarx_adapter),
    config_manager: ConfigService = Depends(get_config_manager),
) -> CalibrationService:
    return CalibrationService(px, config_manager=config_manager)


def get_robot_manager(
    connection_manager: ConnectionService = Depends(get_connection_manager),
    picarx_adapter: PicarxAdapter = Depends(get_picarx_adapter),
    calibration_service: CalibrationService = Depends(get_calibration_service),
    distance_service: DistanceService = Depends(get_distance_service),
) -> CarService:
    return CarService(
        connection_manager=connection_manager,
        px=picarx_adapter,
        calibration_service=calibration_service,
        distance_service=distance_service,
    )
