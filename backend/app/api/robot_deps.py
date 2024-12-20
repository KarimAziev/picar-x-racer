from functools import lru_cache

from app.adapters.pidog.pidog import Pidog
from app.services.car_control.avoid_obstacles_service import AvoidObstaclesService
from app.services.car_control.calibration_service import CalibrationService
from app.services.connection_service import ConnectionService
from app.services.pidog.pidog_service import PidogService
from app.util.logger import Logger
from fastapi import Depends

logger = Logger(__name__)


@lru_cache()
def get_connection_manager() -> ConnectionService:
    return ConnectionService(app_name="px_robot")


def get_robot_adapter() -> Pidog:
    return Pidog()


def get_avoid_obstacles_service(
    px=Depends(get_robot_adapter),
) -> AvoidObstaclesService:
    return AvoidObstaclesService(px=px)


def get_calibration_service(px=Depends(get_robot_adapter)) -> CalibrationService:
    return CalibrationService(px)


def get_robot_manager(
    connection_manager: ConnectionService = Depends(get_connection_manager),
    px_adapter: Pidog = Depends(get_robot_adapter),
) -> PidogService:
    return PidogService(
        connection_manager=connection_manager,
        pidog=px_adapter,
    )
