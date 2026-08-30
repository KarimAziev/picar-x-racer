"""Explicit, bounded autonomous action endpoints."""

from typing import Annotated, Optional

from app.api import robot_deps
from app.schemas.autonomy import RelativeDistanceRequest, RelativeMotionStatus
from app.services.autonomy import ActionConflictError, RelativeMotionService
from fastapi import APIRouter, Depends, HTTPException


router = APIRouter()
RelativeMotionDependency = Annotated[
    Optional[RelativeMotionService], Depends(robot_deps.get_relative_motion_service)
]


def _require_service(
    service: Optional[RelativeMotionService],
) -> RelativeMotionService:
    if service is None:
        raise HTTPException(
            status_code=409,
            detail="relative motion requires motion control and Ackermann odometry",
        )
    return service


@router.get("/px/api/autonomy/relative-motion", response_model=RelativeMotionStatus)
async def get_relative_motion_status(
    service: RelativeMotionDependency,
) -> RelativeMotionStatus:
    return service.status if service else RelativeMotionStatus.unavailable()


@router.post(
    "/px/api/autonomy/relative-motion/distance",
    response_model=RelativeMotionStatus,
)
async def start_relative_distance(
    request: RelativeDistanceRequest,
    service: RelativeMotionDependency,
) -> RelativeMotionStatus:
    try:
        return await _require_service(service).start_distance(request)
    except ActionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/px/api/autonomy/relative-motion/cancel",
    response_model=RelativeMotionStatus,
)
async def cancel_relative_motion(
    service: RelativeMotionDependency,
) -> RelativeMotionStatus:
    return await _require_service(service).cancel()
