"""
API endpoints for retrieving the board pinout.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.core.px_logger import Logger
from app.exceptions.pin import PinFactoryNotAvailable
from app.schemas.robot.pinout import BoardLayout
from app.util.doc_util import build_response_description
from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    from app.services.sensors.pinout_service import PinoutService

router = APIRouter()

_log = Logger(name=__name__)


@router.get(
    "/px/api/pinout",
    summary="Retrieve board pinout",
    response_model=BoardLayout,
    response_description=build_response_description(
        BoardLayout, "Successful response with board pinout and related information."
    ),
)
def get_pinout(
    pinout_service: Annotated["PinoutService", Depends(robot_deps.get_pinout_service)],
) -> BoardLayout:
    """
    Retrieve board pinout that combines board metadata with a mapping of headers to their pins.
    """
    try:
        return pinout_service.board_pinout()
    except PinFactoryNotAvailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        _log.info("Unexpected error while retrieving board pinout", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve board pinout")
