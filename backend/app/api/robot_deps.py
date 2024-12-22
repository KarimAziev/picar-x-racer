from functools import lru_cache

from app.adapters.picarx_adapter import PicarxAdapter
from app.adapters.pidog.pidog import Pidog
from app.services.async_task_manager import AsyncTaskManager
from app.services.car_control.calibration_service import CalibrationService
from app.services.connection_service import ConnectionService
from app.services.distance_service import DistanceService
from app.services.pidog.pidog_service import PidogService
from app.util.async_emitter import AsyncEventEmitter
from app.util.logger import Logger
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


def get_distance_service(
    emitter: AsyncEventEmitter = Depends(get_async_event_emitter),
    task_manager: AsyncTaskManager = Depends(get_async_task_manager),
) -> DistanceService:
    return DistanceService(
        emitter=emitter,
        task_manager=task_manager,
    )


def get_robot_adapter() -> Pidog:
    return Pidog()


def get_picarx_adapter() -> PicarxAdapter:
    return PicarxAdapter()


def get_calibration_service(px=Depends(get_robot_adapter)) -> CalibrationService:
    return CalibrationService(px)


def get_robot_manager(
    connection_manager: ConnectionService = Depends(get_connection_manager),
    picarx_adapter: Pidog = Depends(get_robot_adapter),
    distance_service: DistanceService = Depends(get_distance_service),
) -> PidogService:
    return PidogService(
        connection_manager=connection_manager,
        pidog=picarx_adapter,
        distance_service=distance_service,
    )
