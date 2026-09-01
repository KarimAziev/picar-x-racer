"""Explicit, bounded autonomous action endpoints."""

from typing import Annotated, Optional

from app.api import robot_deps
from app.schemas.autonomy import (
    RelativeArcRequest,
    RelativeDistanceRequest,
    RelativeMotionStatus,
    SimulationPose2D,
    SimulationRuntimeStatus,
    SimulationWorldGeometry,
    SimulationWorldSegment,
)
from app.services.autonomy import (
    AckermannOdometryService,
    ActionConflictError,
    CoherentSimulationSupervisor,
    LocalMappingService,
    MotionControlService,
    RelativeMotionService,
    RobotMode,
)
from fastapi import APIRouter, Depends, HTTPException


router = APIRouter()
RelativeMotionDependency = Annotated[
    Optional[RelativeMotionService], Depends(robot_deps.get_relative_motion_service)
]
SimulationDependency = Annotated[
    CoherentSimulationSupervisor,
    Depends(robot_deps.get_coherent_simulation_supervisor),
]
MotionControlDependency = Annotated[
    Optional[MotionControlService],
    Depends(robot_deps.get_motion_control_service),
]
OdometryDependency = Annotated[
    Optional[AckermannOdometryService], Depends(robot_deps.get_odometry_service)
]
MappingDependency = Annotated[
    Optional[LocalMappingService], Depends(robot_deps.get_local_mapping_service)
]


def _simulation_status(
    simulation: CoherentSimulationSupervisor,
    motion_control: Optional[MotionControlService],
) -> SimulationRuntimeStatus:
    service = simulation.service
    error = service.last_error if service is not None else None
    world = service.world if service is not None else None
    initial_pose = service.initial_pose if service is not None else None
    return SimulationRuntimeStatus(
        enabled=simulation.enabled,
        running=simulation.running,
        physical_drive_isolated=bool(
            motion_control is not None and motion_control.simulation_enabled
        ),
        published_updates=service.published_updates if service is not None else 0,
        lidar_published_updates=(
            service.lidar_published_updates if service is not None else 0
        ),
        world=(
            SimulationWorldGeometry(
                scenario=world.scenario,
                segments=tuple(
                    SimulationWorldSegment(
                        start_x_m=segment.start_x_m,
                        start_y_m=segment.start_y_m,
                        end_x_m=segment.end_x_m,
                        end_y_m=segment.end_y_m,
                    )
                    for segment in world.segments
                ),
            )
            if world is not None
            else None
        ),
        odom_origin_in_world=(
            SimulationPose2D(
                x_m=initial_pose[0],
                y_m=initial_pose[1],
                yaw_rad=initial_pose[2],
            )
            if initial_pose is not None
            else None
        ),
        latest_state=service.latest if service is not None else None,
        error=str(error) if error is not None else None,
    )


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
    "/px/api/autonomy/relative-motion/arc",
    response_model=RelativeMotionStatus,
)
async def start_relative_arc(
    request: RelativeArcRequest,
    service: RelativeMotionDependency,
) -> RelativeMotionStatus:
    try:
        return await _require_service(service).start_arc(request)
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


@router.get(
    "/px/api/autonomy/simulation",
    response_model=SimulationRuntimeStatus,
    summary="Retrieve coherent simulation lifecycle and drive-isolation status",
)
async def get_simulation_status(
    simulation: SimulationDependency,
    motion_control: MotionControlDependency,
) -> SimulationRuntimeStatus:
    return _simulation_status(simulation, motion_control)


@router.post(
    "/px/api/autonomy/simulation/reset",
    response_model=SimulationRuntimeStatus,
    summary="Reset simulated pose after making the current command safe",
)
async def reset_simulation(
    simulation: SimulationDependency,
    motion_control: MotionControlDependency,
    odometry: OdometryDependency,
    mapping: MappingDependency,
) -> SimulationRuntimeStatus:
    if not simulation.enabled:
        raise HTTPException(status_code=409, detail="coherent simulation is disabled")
    if motion_control is None or not motion_control.simulation_enabled:
        raise HTTPException(
            status_code=409,
            detail="physical drive is not isolated for coherent simulation",
        )
    if motion_control.mode not in {RobotMode.ESTOP, RobotMode.FAULT}:
        await motion_control.set_mode(RobotMode.DISARMED)
    else:
        await motion_control.step()
    await simulation.reset()
    if odometry is not None:
        odometry.reset()
    if mapping is not None:
        mapping.reset_session()
    return _simulation_status(simulation, motion_control)
