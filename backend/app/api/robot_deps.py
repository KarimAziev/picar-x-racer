from functools import lru_cache

from app.adapters.picarx_adapter import PicarxAdapter
from app.services.car_control.avoid_obstacles_service import AvoidObstaclesService
from app.services.car_control.calibration_service import CalibrationService
from app.services.car_control.car_service import CarService
from app.services.connection_service import ConnectionService
from app.util.logger import Logger
from fastapi import Depends

logger = Logger(__name__)


@lru_cache()
def get_connection_manager() -> ConnectionService:
    return ConnectionService(app_name="px_robot")


def get_picarx_adapter() -> PicarxAdapter:
    return PicarxAdapter()


def get_avoid_obstacles_service(
    px=Depends(get_picarx_adapter),
) -> AvoidObstaclesService:
    return AvoidObstaclesService(px=px)


def get_calibration_service(px=Depends(get_picarx_adapter)) -> CalibrationService:
    return CalibrationService(px)


def get_robot_manager(
    connection_manager: ConnectionService = Depends(get_connection_manager),
    picarx_adapter: PicarxAdapter = Depends(get_picarx_adapter),
    calibration_service: CalibrationService = Depends(get_calibration_service),
    avolid_obstacles_service: AvoidObstaclesService = Depends(
        get_avoid_obstacles_service
    ),
) -> CarService:
    return CarService(
        connection_manager=connection_manager,
        px=picarx_adapter,
        avolid_obstacles_service=avolid_obstacles_service,
        calibration_service=calibration_service,
    )
