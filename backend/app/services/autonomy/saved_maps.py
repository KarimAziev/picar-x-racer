"""Versioned, atomic occupancy snapshots; loading requires explicit pose alignment."""

from datetime import datetime, timezone
import math
from pathlib import Path
import re
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.autonomy import LocalizationPose2D, OccupancyGrid
from app.util.atomic_write import atomic_write


class MapAlignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x_m: float = Field(allow_inf_nan=False)
    y_m: float = Field(allow_inf_nan=False)
    yaw_deg: float = Field(ge=-180, le=180, allow_inf_nan=False)


class SavedMapInfo(BaseModel):
    id: str = Field(pattern=r"^[a-f0-9]{32}$")
    name: str = Field(min_length=1, max_length=80)
    created_at: str
    saved_pose: Optional[MapAlignment] = None


class SavedMap(SavedMapInfo):
    format_version: Literal[1] = 1
    grid: OccupancyGrid


class SavedMapStore:
    MAX_BYTES = 16 * 1024 * 1024

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _path(self, map_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", map_id):
            raise ValueError("invalid saved-map ID")
        return self.directory / f"{map_id}.json"

    def save(
        self, name: str, grid: OccupancyGrid, pose: Optional[LocalizationPose2D]
    ) -> SavedMapInfo:
        if grid.width * grid.height > 1_000_000 or not any(
            value >= 0 for value in grid.data
        ):
            raise ValueError(
                "only nonempty maps of at most one million cells can be saved"
            )
        snapshot = SavedMap(
            id=uuid.uuid4().hex,
            name=name.strip(),
            created_at=datetime.now(timezone.utc).isoformat(),
            grid=grid,
            saved_pose=(
                MapAlignment(
                    x_m=pose.x_m, y_m=pose.y_m, yaw_deg=math.degrees(pose.yaw_rad)
                )
                if pose
                else None
            ),
        )
        data = snapshot.model_dump_json()
        if len(data.encode("utf-8")) > self.MAX_BYTES:
            raise ValueError("map snapshot exceeds the size limit")
        with atomic_write(self._path(snapshot.id), encoding="utf-8") as stream:
            stream.write(data)
        return SavedMapInfo.model_validate(snapshot.model_dump())

    def load(self, map_id: str) -> SavedMap:
        path = self._path(map_id)
        with path.open("rb") as stream:
            data = stream.read(self.MAX_BYTES + 1)
        if len(data) > self.MAX_BYTES:
            raise ValueError("saved map exceeds the size limit")
        snapshot = SavedMap.model_validate_json(data)
        if (
            snapshot.id != map_id
            or snapshot.grid.width * snapshot.grid.height > 1_000_000
        ):
            raise ValueError("saved-map identity or dimensions are invalid")
        return snapshot

    def list(self) -> list[SavedMapInfo]:
        snapshots = [
            SavedMapInfo.model_validate(self.load(path.stem).model_dump())
            for path in sorted(self.directory.glob("*.json"), reverse=True)
            if re.fullmatch(r"[a-f0-9]{32}", path.stem)
        ]
        return sorted(snapshots, key=lambda item: item.created_at, reverse=True)


def align_saved_grid(
    grid: OccupancyGrid, alignment: MapAlignment, current: LocalizationPose2D
) -> OccupancyGrid:
    """Place the operator-specified saved-map robot pose at its current odom pose."""
    dx, dy = alignment.x_m - grid.origin_x_m, alignment.y_m - grid.origin_y_m
    c, s = math.cos(grid.origin_yaw_rad), math.sin(grid.origin_yaw_rad)
    column = math.floor((c * dx + s * dy) / grid.resolution_m)
    row = math.floor((-s * dx + c * dy) / grid.resolution_m)
    if not (0 <= column < grid.width and 0 <= row < grid.height):
        raise ValueError("robot placement is outside the saved map")
    if not 0 <= grid.data[row * grid.width + column] < 50:
        raise ValueError("robot placement must be in known free saved-map space")
    angle = current.yaw_rad - math.radians(alignment.yaw_deg)
    c, s = math.cos(angle), math.sin(angle)
    dx, dy = grid.origin_x_m - alignment.x_m, grid.origin_y_m - alignment.y_m
    return grid.model_copy(
        update={
            "origin_x_m": current.x_m + c * dx - s * dy,
            "origin_y_m": current.y_m + s * dx + c * dy,
            "origin_yaw_rad": (grid.origin_yaw_rad + angle + math.pi) % (2 * math.pi)
            - math.pi,
        }
    )
