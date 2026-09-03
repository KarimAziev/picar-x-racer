"""Explicit, bounded autonomous action endpoints."""

from typing import Annotated, Optional

from app.api import robot_deps
from app.schemas.autonomy import (
    NavigationGoalRequest,
    NavigationExecutionRequest,
    NavigationExecutionStatus,
    NavigationPlanStatus,
    RelativeArcRequest,
    RelativeDistanceRequest,
    RelativeMotionStatus,
    LocalizationRuntimeStatus,
    ScanMatchingRuntimeStatus,
    SimulationPose2D,
    SimulationRuntimeStatus,
    SimulationSensorImperfectionStatus,
    SimulationWorldGeometry,
    SimulationWorldSegment,
)
from app.services.autonomy import (
    AckermannOdometryService,
    ActionConflictError,
    CoherentSimulationSupervisor,
    LocalMappingService,
    MotionControlService,
    NavigationPlanningService,
    NavigationExecutionService,
    PoseEstimatorSupervisor,
    KnownWorldScanMatcherSupervisor,
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
PoseEstimatorDependency = Annotated[
    PoseEstimatorSupervisor,
    Depends(robot_deps.get_pose_estimator_supervisor),
]
ScanMatcherDependency = Annotated[
    KnownWorldScanMatcherSupervisor,
    Depends(robot_deps.get_known_world_scan_matcher_supervisor),
]
NavigationPlanningDependency = Annotated[
    NavigationPlanningService,
    Depends(robot_deps.get_navigation_planning_service),
]
NavigationExecutionDependency = Annotated[
    Optional[NavigationExecutionService],
    Depends(robot_deps.get_navigation_execution_service),
]


def _simulation_status(
    simulation: CoherentSimulationSupervisor,
    motion_control: Optional[MotionControlService],
) -> SimulationRuntimeStatus:
    service = simulation.service
    error = service.last_error if service is not None else None
    world = service.world if service is not None else None
    initial_pose = service.initial_pose if service is not None else None
    sensor_model = service.sensor_imperfections if service is not None else None
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
        sensor_imperfections=(
            SimulationSensorImperfectionStatus(
                enabled=sensor_model.enabled,
                random_seed=sensor_model.random_seed,
                encoder_scale_error_percent=(sensor_model.encoder_scale_error_percent),
                encoder_noise_stddev_ticks=(sensor_model.encoder_noise_stddev_ticks),
                steering_bias_deg=sensor_model.steering_bias_deg,
                steering_noise_stddev_deg=(sensor_model.steering_noise_stddev_deg),
                imu_yaw_rate_bias_radps=sensor_model.imu_yaw_rate_bias_radps,
                imu_yaw_rate_noise_stddev_radps=(
                    sensor_model.imu_yaw_rate_noise_stddev_radps
                ),
                lidar_range_noise_stddev_m=(sensor_model.lidar_range_noise_stddev_m),
                lidar_dropout_probability=(sensor_model.lidar_dropout_probability),
            )
            if sensor_model is not None
            else None
        ),
        latest_state=service.latest if service is not None else None,
        error=str(error) if error is not None else None,
    )


def _localization_status(
    supervisor: PoseEstimatorSupervisor,
) -> LocalizationRuntimeStatus:
    service = supervisor.service
    error = service.last_error if service is not None else None
    return LocalizationRuntimeStatus(
        enabled=supervisor.enabled,
        running=supervisor.running,
        published_updates=service.published_updates if service is not None else 0,
        imu_updates_used=service.imu_updates_used if service is not None else 0,
        imu_updates_rejected=(
            service.imu_updates_rejected if service is not None else 0
        ),
        corrections_applied=service.corrections_applied if service is not None else 0,
        corrections_rejected=(
            service.corrections_rejected if service is not None else 0
        ),
        last_position_innovation_m=(
            service.last_position_innovation_m if service is not None else None
        ),
        last_heading_innovation_rad=(
            service.last_heading_innovation_rad if service is not None else None
        ),
        latest_pose=service.latest if service is not None else None,
        error=str(error) if error is not None else None,
    )


def _scan_matching_status(
    supervisor: KnownWorldScanMatcherSupervisor,
) -> ScanMatchingRuntimeStatus:
    service = supervisor.service
    error = service.last_error if service is not None else None
    return ScanMatchingRuntimeStatus(
        enabled=supervisor.enabled,
        running=supervisor.running,
        scans_received=service.scans_received if service is not None else 0,
        matches_published=service.matches_published if service is not None else 0,
        rejected_missing_pose=(
            service.rejected_missing_pose if service is not None else 0
        ),
        rejected_pose_timing=(
            service.rejected_pose_timing if service is not None else 0
        ),
        rejected_insufficient_points=(
            service.rejected_insufficient_points if service is not None else 0
        ),
        rejected_quality=service.rejected_quality if service is not None else 0,
        last_mean_error_m=service.last_mean_error_m if service is not None else None,
        last_prior_mean_error_m=(
            service.last_prior_mean_error_m if service is not None else None
        ),
        last_valid_points=service.last_valid_points if service is not None else 0,
        last_candidates_evaluated=(
            service.last_candidates_evaluated if service is not None else 0
        ),
        latest_observation=(
            service.latest_observation if service is not None else None
        ),
        last_rejection=service.last_rejection if service is not None else None,
        error=str(error) if error is not None else None,
    )


def _require_relative_service(
    service: Optional[RelativeMotionService],
) -> RelativeMotionService:
    if service is None:
        raise HTTPException(
            status_code=409,
            detail="relative motion requires motion control and Ackermann odometry",
        )
    return service


def _require_navigation_execution_service(
    service: Optional[NavigationExecutionService],
) -> NavigationExecutionService:
    if service is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "navigation requires motion control, fused localization, and "
                "Ackermann geometry"
            ),
        )
    return service


@router.get(
    "/px/api/autonomy/navigation/plan",
    response_model=NavigationPlanStatus,
    summary="Retrieve the latest non-driving navigation route preview",
)
async def get_navigation_plan(
    service: NavigationPlanningDependency,
) -> NavigationPlanStatus:
    return service.status


@router.post(
    "/px/api/autonomy/navigation/plan",
    response_model=NavigationPlanStatus,
    summary="Plan a collision-aware route without moving the vehicle",
)
async def plan_navigation_goal(
    request: NavigationGoalRequest,
    service: NavigationPlanningDependency,
) -> NavigationPlanStatus:
    return await service.plan(request)


@router.post(
    "/px/api/autonomy/navigation/plan/clear",
    response_model=NavigationPlanStatus,
    summary="Clear the current navigation route preview",
)
async def clear_navigation_plan(
    service: NavigationPlanningDependency,
) -> NavigationPlanStatus:
    return await service.clear()


@router.get(
    "/px/api/autonomy/navigation/execution",
    response_model=NavigationExecutionStatus,
    summary="Retrieve the current navigation execution state",
)
async def get_navigation_execution(
    service: NavigationExecutionDependency,
) -> NavigationExecutionStatus:
    return service.status if service else NavigationExecutionStatus.unavailable()


@router.post(
    "/px/api/autonomy/navigation/execution/start",
    response_model=NavigationExecutionStatus,
    summary="Start following the currently reviewed route",
)
async def start_navigation_execution(
    request: NavigationExecutionRequest,
    service: NavigationExecutionDependency,
) -> NavigationExecutionStatus:
    try:
        return await _require_navigation_execution_service(service).start(request)
    except ActionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/px/api/autonomy/navigation/execution/pause",
    response_model=NavigationExecutionStatus,
)
async def pause_navigation_execution(
    service: NavigationExecutionDependency,
) -> NavigationExecutionStatus:
    try:
        return await _require_navigation_execution_service(service).pause()
    except ActionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/px/api/autonomy/navigation/execution/resume",
    response_model=NavigationExecutionStatus,
)
async def resume_navigation_execution(
    service: NavigationExecutionDependency,
) -> NavigationExecutionStatus:
    try:
        return await _require_navigation_execution_service(service).resume()
    except ActionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/px/api/autonomy/navigation/execution/cancel",
    response_model=NavigationExecutionStatus,
)
async def cancel_navigation_execution(
    service: NavigationExecutionDependency,
) -> NavigationExecutionStatus:
    return await _require_navigation_execution_service(service).cancel()


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
        return await _require_relative_service(service).start_distance(request)
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
        return await _require_relative_service(service).start_arc(request)
    except ActionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/px/api/autonomy/relative-motion/cancel",
    response_model=RelativeMotionStatus,
)
async def cancel_relative_motion(
    service: RelativeMotionDependency,
) -> RelativeMotionStatus:
    return await _require_relative_service(service).cancel()


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


@router.get(
    "/px/api/autonomy/localization",
    response_model=LocalizationRuntimeStatus,
    summary="Retrieve pose-fusion lifecycle, health, and uncertainty",
)
async def get_localization_status(
    estimator: PoseEstimatorDependency,
) -> LocalizationRuntimeStatus:
    return _localization_status(estimator)


@router.get(
    "/px/api/autonomy/localization/scan-matching",
    response_model=ScanMatchingRuntimeStatus,
    summary="Retrieve simulation known-world scan-matching quality and health",
)
async def get_scan_matching_status(
    matcher: ScanMatcherDependency,
) -> ScanMatchingRuntimeStatus:
    return _scan_matching_status(matcher)


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
    estimator: PoseEstimatorDependency,
    matcher: ScanMatcherDependency,
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
    await estimator.reset()
    await matcher.reset()
    return _simulation_status(simulation, motion_control)
