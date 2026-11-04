"""Guided measurement sessions with explicit review and application."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from app.api import robot_deps
from app.api.control.settings import _reload_running_autonomy_from_app
from app.exceptions.settings import InvalidSettings, UnchangedSettings
from app.schemas.autonomy.calibration import (
    CalibrationApply,
    CalibrationFinish,
    CalibrationHeartbeat,
    CalibrationKind,
    CalibrationStart,
    CalibrationStatus,
)
from app.services.autonomy.calibration import CalibrationError, GuidedCalibrationService
from app.services.connection_service import ConnectionService
from app.schemas.robot.config import PartialHardwareConfig
from pydantic import ValidationError

router = APIRouter()
Service = Annotated[
    GuidedCalibrationService, Depends(robot_deps.get_guided_calibration_service)
]


def display_error(error: Exception) -> HTTPException:
    if isinstance(error, ValidationError):
        message = " ".join(
            str(item["msg"]).removeprefix("Value error, ")
            for item in error.errors(include_url=False)
        )
    else:
        message = str(error)
    return HTTPException(status_code=409, detail=message)


@router.get("/px/api/calibration/status", response_model=CalibrationStatus)
async def status(
    service: Service,
    kind: CalibrationKind = "wheel_distance",
    direction: Literal["forward", "reverse"] = "forward",
    stop_distance_m: Annotated[float, Query(ge=0.2, le=5)] = 0.6,
):
    result = service.status(kind, direction=direction, stop_distance_m=stop_distance_m)
    # The session token is returned only to the client that starts the trial.
    result.session_id = None
    return result


@router.post("/px/api/calibration/start", response_model=CalibrationStatus)
async def start(data: CalibrationStart, service: Service):
    try:
        return await service.start(data)
    except (CalibrationError, RuntimeError) as error:
        raise display_error(error) from error


@router.post(
    "/px/api/calibration/{session_id}/heartbeat", response_model=CalibrationStatus
)
async def heartbeat(session_id: str, data: CalibrationHeartbeat, service: Service):
    try:
        return await service.heartbeat(session_id, data)
    except CalibrationError as error:
        raise display_error(error) from error


@router.post(
    "/px/api/calibration/{session_id}/finish", response_model=CalibrationStatus
)
async def finish(session_id: str, data: CalibrationFinish, service: Service):
    try:
        return await service.finish(session_id, data)
    except CalibrationError as error:
        raise display_error(error) from error


@router.post(
    "/px/api/calibration/{session_id}/cancel", response_model=CalibrationStatus
)
async def cancel(session_id: str, service: Service):
    try:
        return await service.cancel(session_id)
    except CalibrationError as error:
        raise display_error(error) from error


@router.post("/px/api/calibration/preview")
async def preview(data: CalibrationApply, service: Service):
    try:
        update = service.proposed_update(data)
        service.settings.build_merged_settings(
            PartialHardwareConfig.model_validate(update)
        )
        return update
    except (CalibrationError, InvalidSettings, ValidationError) as error:
        raise display_error(error) from error


@router.post("/px/api/calibration/apply", response_model=CalibrationStatus)
async def apply(
    request: Request,
    data: CalibrationApply,
    service: Service,
    connection: Annotated[
        ConnectionService, Depends(robot_deps.get_connection_manager)
    ],
):
    previous = service.settings.saved_settings.model_copy(deep=True)
    try:
        result = await service.apply(data)
    except (
        CalibrationError,
        InvalidSettings,
        UnchangedSettings,
        ValidationError,
    ) as error:
        raise display_error(error) from error
    await _reload_running_autonomy_from_app(
        request, previous, service.settings.saved_settings
    )
    await connection.broadcast_json(
        {"type": "robot_partial_settings", "payload": result.saved_config}
    )
    return result
