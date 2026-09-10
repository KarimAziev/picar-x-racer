"""Explicit save/load of frozen maps, never automatic pose restoration or motion."""

import asyncio
from pathlib import Path
import time
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api import robot_deps
from app.config.config import settings
from app.schemas.autonomy import (
    MappingSessionState,
    MappingSessionStatus,
    LocalizationPose2D,
)
from app.services.autonomy import (
    LocalMappingService,
    MotionControlService,
    NavigationExecutionService,
    NavigationMissionService,
    RobotMode,
    TopicBus,
)
from app.services.autonomy.saved_maps import (
    SavedMapInfo,
    SavedMapStore,
    MapAlignment,
    align_saved_grid,
)
from app.services.autonomy.topics import LOCAL_MAP, LOCALIZATION_POSE

router = APIRouter()


def get_saved_map_store() -> SavedMapStore:
    return SavedMapStore(Path(settings.ROBOT_CONFIG_FILE).parent / "autonomy-maps")


class SaveMapRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


StoreDep = Annotated[SavedMapStore, Depends(get_saved_map_store)]
BusDep = Annotated[TopicBus, Depends(robot_deps.get_robot_topic_bus)]
MappingDep = Annotated[
    Optional[LocalMappingService], Depends(robot_deps.get_local_mapping_service)
]


@router.get("/px/api/maps", response_model=list[SavedMapInfo])
async def list_maps(store: StoreDep) -> list[SavedMapInfo]:
    try:
        return await asyncio.to_thread(store.list)
    except (OSError, ValueError) as error:
        raise HTTPException(409, f"Unable to read saved maps: {error}") from error


@router.post("/px/api/maps", response_model=SavedMapInfo)
async def save_map(
    request: SaveMapRequest, store: StoreDep, bus: BusDep, mapping: MappingDep
) -> SavedMapInfo:
    grid = bus.latest(LOCAL_MAP)
    if (
        mapping is None
        or mapping.status.state == MappingSessionState.ACTIVE
        or not mapping.status.has_map
        or grid is None
    ):
        raise HTTPException(
            409, "pause or finish a nonempty mapping session before saving"
        )
    pose = bus.latest(LOCALIZATION_POSE)
    if pose is not None and (
        pose.header.frame_id != grid.header.frame_id
        or not 0
        <= time.monotonic_ns() - pose.header.timestamp_monotonic_ns
        <= 500_000_000
    ):
        pose = None
    try:
        return await asyncio.to_thread(store.save, request.name, grid, pose)
    except (OSError, ValueError) as error:
        raise HTTPException(409, f"Unable to save map: {error}") from error


@router.post("/px/api/maps/{map_id}/load", response_model=MappingSessionStatus)
async def load_map(
    map_id: str,
    alignment: MapAlignment,
    store: StoreDep,
    bus: BusDep,
    mapping: MappingDep,
    motion: Annotated[
        Optional[MotionControlService], Depends(robot_deps.get_motion_control_service)
    ],
    navigation: Annotated[
        Optional[NavigationExecutionService],
        Depends(robot_deps.get_navigation_execution_service),
    ],
    mission: Annotated[
        NavigationMissionService, Depends(robot_deps.get_navigation_mission_service)
    ],
) -> MappingSessionStatus:
    def require_safe_pose() -> LocalizationPose2D:
        if mapping is None or mapping.status.state == MappingSessionState.ACTIVE:
            raise HTTPException(
                409, "enable mapping, then pause or finish it before loading"
            )
        if (
            motion is None
            or motion.mode != RobotMode.DISARMED
            or (navigation is not None and navigation.running)
            or mission.running
        ):
            raise HTTPException(
                409, "disarm the robot and cancel navigation before loading a map"
            )
        pose = bus.latest(LOCALIZATION_POSE)
        if (
            pose is None
            or pose.header.frame_id != "odom"
            or not 0
            <= time.monotonic_ns() - pose.header.timestamp_monotonic_ns
            <= 500_000_000
        ):
            raise HTTPException(
                409, "fresh fused localization is required to align a saved map"
            )
        return pose

    require_safe_pose()
    assert motion is not None and mapping is not None
    generation = motion.mode_generation
    try:
        snapshot = await asyncio.to_thread(store.load, map_id)
    except FileNotFoundError as error:
        raise HTTPException(404, "saved map not found") from error
    except (OSError, ValueError) as error:
        raise HTTPException(409, f"Unable to load map: {error}") from error
    pose = require_safe_pose()
    if motion.mode_generation != generation:
        raise HTTPException(
            409, "robot mode changed while loading; check placement and retry"
        )
    try:
        aligned = align_saved_grid(snapshot.grid, alignment, pose)
        return mapping.load_frozen_grid(aligned)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
