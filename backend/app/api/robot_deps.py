from functools import lru_cache

from app.adapters.picarx_adapter import PicarxAdapter
from app.services.async_task_manager import AsyncTaskManager
from app.services.car_control.avoid_obstacles_service import AvoidObstaclesService
from app.services.car_control.calibration_service import CalibrationService
from app.services.car_control.car_service import CarService
from app.services.connection_service import ConnectionService
from app.services.distance_service import DistanceService
from app.util.async_emitter import AsyncEventEmitter
from app.util.logger import Logger
from fastapi import Depends

logger = Logger(__name__)


@lru_cache()
def get_connection_manager() -> ConnectionService:
    return ConnectionService(app_name="px_robot")


@lru_cache()
def get_async_event_emitter() -> AsyncEventEmitter:
    logger.info("GETTING ASYNC EVENT EMITTER")
    return AsyncEventEmitter()


@lru_cache()
def get_async_task_manager() -> AsyncTaskManager:
    logger.info("GETTING TASK MANAGER")
    return AsyncTaskManager()


def get_distance_service(
    emitter: AsyncEventEmitter = Depends(get_async_event_emitter),
    task_manager: AsyncTaskManager = Depends(get_async_task_manager),
) -> DistanceService:
    return DistanceService(
        emitter=emitter, task_manager=task_manager, trig_pin="D2", echo_pin="D3"
    )


def get_picarx_adapter() -> PicarxAdapter:
    return PicarxAdapter()


def get_avoid_obstacles_service(
    px=Depends(get_picarx_adapter),
    distance_service=Depends(get_distance_service),
) -> AvoidObstaclesService:
    return AvoidObstaclesService(px=px, distance_service=distance_service)


def get_calibration_service(px=Depends(get_picarx_adapter)) -> CalibrationService:
    return CalibrationService(px)


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
