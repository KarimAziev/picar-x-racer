"""Opt-in diagnostic recording; no endpoints can replay commands to hardware."""

import asyncio
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re
import subprocess
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api import robot_deps
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.autonomy.recording import RecordingStatus
from app.services.autonomy.recording import AutonomyRecorder

router = APIRouter(prefix="/px/api/autonomy/recordings")
RecorderDependency = Annotated[
    AutonomyRecorder, Depends(robot_deps.get_autonomy_recorder)
]
ConfigDependency = Annotated[JsonDataManager, Depends(robot_deps.get_config_manager)]


def software_versions() -> dict[str, str]:
    result = {}
    try:
        result["robot_hat"] = version("robot-hat")
    except PackageNotFoundError:
        result["robot_hat"] = "unknown"
    try:
        root = Path(__file__).resolve().parents[4]
        result["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        result["git_tracked_dirty"] = str(
            bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain", "--untracked-files=no"],
                    cwd=root,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                ).strip()
            )
        ).lower()
    except (OSError, subprocess.SubprocessError):
        result["git_commit"] = "unknown"
    return result


@router.get("/status")
async def recording_status(recorder: RecorderDependency) -> RecordingStatus:
    return recorder.status


@router.post("/start")
async def start_recording(
    recorder: RecorderDependency, config: ConfigDependency
) -> RecordingStatus:
    try:
        return await recorder.start(
            config.load_data(), await asyncio.to_thread(software_versions)
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(
            status_code=503, detail="Unable to create a recording file"
        ) from error


@router.post("/stop")
async def stop_recording(recorder: RecorderDependency) -> RecordingStatus:
    return await recorder.stop()


@router.get("/{session_id}/download")
async def download_recording(
    session_id: str, recorder: RecorderDependency
) -> FileResponse:
    if not re.fullmatch(r"[0-9a-f]{32}", session_id):
        raise HTTPException(status_code=404, detail="Unknown recording")
    if recorder.status.active and recorder.status.session_id == session_id:
        raise HTTPException(status_code=409, detail="Stop recording before downloading")
    path = recorder.directory / f"{session_id}.jsonl"
    if path.is_symlink() or not path.is_file():
        raise HTTPException(status_code=404, detail="Unknown recording")
    return FileResponse(path, media_type="application/x-ndjson", filename=path.name)
