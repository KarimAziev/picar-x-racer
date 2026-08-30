"""
Endpoints with robot-specific settings and calibration.
"""

import asyncio
from typing import Annotated, Any, Dict, Optional

from app.api import robot_deps
from app.core.px_logger import Logger
from app.exceptions.settings import InvalidSettings, UnchangedSettings
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.robot.calibration import CalibrationConfig
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.services.connection_service import ConnectionService
from app.services.autonomy import (
    AckermannOdometryService,
    LidarSafetyService,
    LocalizationSensorService,
    LocalMappingService,
    MotionControlService,
    SteeringFeedbackService,
    TopicBus,
)
from app.services.control.settings_service import SettingsService
from app.util.doc_util import build_response_description
from fastapi import APIRouter, Depends, HTTPException, Request
from robot_hat.i2c.smbus_manager import SMBusManager

router = APIRouter()

_log = Logger(name=__name__)


async def _reload_autonomy_runtime(
    previous: HardwareConfig,
    current: HardwareConfig,
    sensor_service: LocalizationSensorService,
    topic_bus: TopicBus,
    smbus_manager: SMBusManager,
    steering_feedback_service: Optional[SteeringFeedbackService],
    odometry_service: Optional[AckermannOdometryService],
    motion_control_service: Optional[MotionControlService],
    lidar_safety_service: Optional[LidarSafetyService],
    local_mapping_service: Optional[LocalMappingService],
) -> None:
    encoder_changed = (
        previous.localization_sensors.encoder != current.localization_sensors.encoder
    )
    lidar_geometry_changed = (
        previous.localization_sensors.lidar.transform
        != current.localization_sensors.lidar.transform
    )
    if previous.localization_sensors != current.localization_sensors:
        replacement = robot_deps.build_localization_sensor_service(
            current,
            topic_bus,
            smbus_manager,
        )
        await sensor_service.reconfigure_from(replacement)

    previous_steering = previous.localization_sensors.steering
    current_steering = current.localization_sensors.steering
    if (
        previous_steering != current_steering
        and previous_steering.enabled
        and current_steering.enabled
        and steering_feedback_service is not None
    ):
        replacement_steering = robot_deps.build_steering_feedback_service(
            current,
            smbus_manager,
        )
        if replacement_steering is not None:
            await steering_feedback_service.reconfigure_from(replacement_steering)

    if (
        (previous.ackermann_odometry != current.ackermann_odometry or encoder_changed)
        and previous.ackermann_odometry.enabled
        and current.ackermann_odometry.enabled
        and odometry_service is not None
    ):
        estimator = robot_deps.build_odometry_estimator(current)
        odometry_service.reconfigure(estimator.config)

    if (
        (previous.lidar_safety != current.lidar_safety or lidar_geometry_changed)
        and previous.lidar_safety.enabled
        and current.lidar_safety.enabled
        and lidar_safety_service is not None
    ):
        replacement_safety = robot_deps.build_lidar_safety_service(
            current,
            topic_bus,
            motion_control_service,
        )
        if replacement_safety is not None:
            lidar_safety_service.reconfigure_from(replacement_safety)

    if (
        (
            previous.local_mapping != current.local_mapping
            or previous.ackermann_odometry != current.ackermann_odometry
            or encoder_changed
            or lidar_geometry_changed
            or previous_steering != current_steering
        )
        and previous.local_mapping.enabled
        and current.local_mapping.enabled
        and local_mapping_service is not None
    ):
        replacement_mapping = robot_deps.build_local_mapping_service(
            current,
            topic_bus,
        )
        if replacement_mapping is not None:
            await local_mapping_service.reconfigure_from(replacement_mapping)


async def _reload_running_autonomy_from_app(
    request: Request,
    previous: HardwareConfig,
    current: HardwareConfig,
) -> None:
    """Apply settings to the exact service instances owned by app lifespan."""

    state = request.app.state
    sensor_service = getattr(state, "localization_sensor_service", None)
    topic_bus = getattr(state, "robot_topic_bus", None)
    smbus_manager = getattr(state, "robot_smbus_manager", None)
    if (
        not isinstance(sensor_service, LocalizationSensorService)
        or not isinstance(topic_bus, TopicBus)
        or not isinstance(smbus_manager, SMBusManager)
    ):
        return
    await _reload_autonomy_runtime(
        previous,
        current,
        sensor_service,
        topic_bus,
        smbus_manager,
        getattr(state, "steering_feedback_service", None),
        getattr(state, "odometry_service", None),
        getattr(state, "motion_control_service", None),
        getattr(state, "lidar_safety_service", None),
        getattr(state, "local_mapping_service", None),
    )


@router.get(
    "/px/api/settings/json-schema",
    response_model=Dict[str, Any],
    summary="Retrieve JSON schema of hardware configuration fields. ",
    responses={
        200: {
            "description": "A JSON schema with extra properties for UI.",
            "content": {
                "application/json": {"example": HardwareConfig.model_json_schema()}
            },
        },
    },
)
def get_json_schema():
    """
    Retrieve the a JSON-like schema representation of robot config settings.

    Used for dynamic rendering of corresponding settings on the UI.
    """
    return HardwareConfig.model_json_schema()


@router.get(
    "/px/api/settings/config",
    response_model=HardwareConfig,
    summary="Retrieve the saved or default robot configuration",
    response_description=build_response_description(
        HardwareConfig, "Successful response with the robot configuration."
    ),
)
def get_config_settings(
    config_manager: Annotated[
        "JsonDataManager", Depends(robot_deps.get_config_manager)
    ],
):
    """
    Retrieve currently saved or default robot configuration.
    """
    _log.debug("Retrieving robot config settings")
    data = config_manager.load_data()
    return data


@router.put(
    "/px/api/settings/config",
    response_model=HardwareConfig,
    summary="Update robot settings.",
    response_description=build_response_description(
        HardwareConfig, "Successful response with the robot configuration."
    ),
)
async def update_settings(
    request: Request,
    settings: HardwareConfig,
    settings_service: Annotated[
        "SettingsService", Depends(robot_deps.get_robot_settings_service)
    ],
    connection_manager: Annotated[
        "ConnectionService", Depends(robot_deps.get_connection_manager)
    ],
):
    """
    Update robot settings.
    """
    _log.info("Saving robot hardware settings")
    previous = getattr(settings_service, "saved_settings", None)
    if isinstance(previous, HardwareConfig):
        previous = previous.model_copy(deep=True)
    try:
        data = await asyncio.to_thread(settings_service.save_settings, settings)
        if isinstance(previous, HardwareConfig):
            await _reload_running_autonomy_from_app(request, previous, data)
    except (UnchangedSettings, InvalidSettings) as err:
        err_msg = str(err)
        _log.error(err_msg)
        raise HTTPException(status_code=409, detail=err_msg)
    except Exception:
        _log.error("Unhandled error while saving settings", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    await connection_manager.broadcast_json(
        {"payload": data.model_dump(mode="json"), "type": "robot_settings"}
    )
    return data


@router.patch(
    "/px/api/settings/config",
    response_model=PartialHardwareConfig,
    summary="Merge partial robot settings.",
    response_description=build_response_description(
        PartialHardwareConfig,
        "Successful response with the partial robot configuration.",
    ),
)
async def merge_partial_settings(
    request: Request,
    settings: PartialHardwareConfig,
    settings_service: Annotated[
        "SettingsService", Depends(robot_deps.get_robot_settings_service)
    ],
    connection_manager: Annotated[
        "ConnectionService", Depends(robot_deps.get_connection_manager)
    ],
):
    """
    Merge partial robot settings with saved configuration.
    """
    _log.info("Saving partial robot hardware settings")
    previous = getattr(settings_service, "saved_settings", None)
    if isinstance(previous, HardwareConfig):
        previous = previous.model_copy(deep=True)

    try:
        partial_settings = await asyncio.to_thread(
            settings_service.merge_settings, settings
        )
        current = getattr(settings_service, "saved_settings", None)
        if isinstance(previous, HardwareConfig) and isinstance(current, HardwareConfig):
            await _reload_running_autonomy_from_app(request, previous, current)
    except (UnchangedSettings, InvalidSettings) as err:
        err_msg = str(err)
        _log.error(err_msg)
        raise HTTPException(status_code=409, detail=err_msg)
    except Exception:
        _log.error("Unhandled error during merging settings", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    await connection_manager.broadcast_json(
        {
            "payload": partial_settings.model_dump(mode="json", exclude_unset=True),
            "type": "robot_partial_settings",
        }
    )
    return partial_settings


@router.get(
    "/px/api/settings/calibration",
    response_model=CalibrationConfig,
    summary="Retrieve saved (or default) calibration settings.",
)
def get_calibration_settings(
    config_manager: Annotated[
        "JsonDataManager", Depends(robot_deps.get_config_manager)
    ],
):
    """
    Retrieve saved calibration settings.
    """
    _log.debug("Retrieving robot calibration settings")
    config = config_manager.load_data()
    return {
        "steering_servo_offset": config.get("steering_servo", {}).get(
            "calibration_offset"
        ),
        "cam_tilt_servo_offset": config.get("cam_tilt_servo", {}).get(
            "calibration_offset"
        ),
        "cam_pan_servo_offset": config.get("cam_pan_servo", {}).get(
            "calibration_offset"
        ),
        "motor_directions": [
            motor.get("calibration_direction", 1) for motor in config.get("motors", [])
        ],
    }
