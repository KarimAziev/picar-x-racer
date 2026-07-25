"""
Endpoints related to text to speech functionalities.
"""

import asyncio
from typing import TYPE_CHECKING, Annotated, List

from app.api import deps
from app.core.logger import Logger
from app.exceptions.tts import TextToSpeechRequestError, TextToSpeechUnavailable
from app.schemas.common import Message
from app.schemas.tts import LanguageOption, TextToSpeechData
from fastapi import APIRouter, Depends, HTTPException, Request, status

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.media.tts_service import TTSService

router = APIRouter()
_log = Logger(__name__)


@router.post(
    "/tts/speak",
    summary="Speak the given text using Google Translate TTS API",
    response_description="The speech request was accepted.",
    response_model=Message,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {
            "description": "The text or language is invalid.",
            "content": {
                "application/json": {
                    "example": {"detail": "Unsupported language: invalid"}
                }
            },
        },
        503: {
            "description": "The text-to-speech player is unavailable.",
            "content": {
                "application/json": {"example": {"detail": "SpeechPlayer is closed"}}
            },
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {"example": {"detail": "Failed to speak the text"}}
            },
        },
    },
)
async def text_to_speech(
    request: Request,
    payload: TextToSpeechData,
    tts_manager: Annotated["TTSService", Depends(deps.get_tts_service)],
):
    """
    Endpoint to convert text to speech.

    The request returns immediately. If speech is already active, it is
    interrupted and replaced by this request. All connected clients are
    notified asynchronously via WebSocket.
    """
    text = payload.text
    lang = payload.lang or "en"
    _log.info("TTS request received: lang=%s chars=%d", lang, len(text))

    try:
        tts_manager.speak(text, lang)
    except TextToSpeechRequestError as error:
        _log.warning("Invalid text-to-speech request: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except TextToSpeechUnavailable as error:
        _log.error("Text-to-speech player is unavailable: %s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        _log.error("Unexpected text-to-speech submission error", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to speak the text",
        ) from error

    connection_manager: "ConnectionService" = request.app.state.app_manager
    try:
        await connection_manager.broadcast_json(
            {"type": "info", "payload": "Speaking: " + text}
        )
    except Exception:
        _log.warning("Unable to broadcast text-to-speech status", exc_info=True)

    return {"message": text}


@router.post(
    "/tts/stop",
    summary="Stop active text-to-speech playback",
    response_description="Whether active or pending speech was stopped.",
    response_model=Message,
    responses={
        503: {
            "description": "The player did not stop within the allowed time.",
            "content": {
                "application/json": {
                    "example": {"detail": "Text-to-speech player did not stop in time"}
                }
            },
        },
    },
)
async def stop_text_to_speech(
    request: Request,
    tts_manager: Annotated["TTSService", Depends(deps.get_tts_service)],
):
    """Interrupt active speech and discard pending speech requests."""
    try:
        stopped = await asyncio.to_thread(
            tts_manager.stop,
            wait=True,
            timeout=5.0,
        )
    except TimeoutError as error:
        _log.error("Text-to-speech player did not stop in time")
        raise HTTPException(
            status_code=503,
            detail="Text-to-speech player did not stop in time",
        ) from error
    except Exception as error:
        _log.error("Unexpected text-to-speech stop error", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to stop text-to-speech playback",
        ) from error

    message = "Speech stopped" if stopped else "No speech was active"
    if stopped:
        connection_manager: "ConnectionService" = request.app.state.app_manager
        try:
            await connection_manager.broadcast_json(
                {"type": "info", "payload": message}
            )
        except Exception:
            _log.warning("Unable to broadcast text-to-speech stop", exc_info=True)

    return {"message": message}


@router.get(
    "/tts/languages",
    response_description="Structured list of supported languages",
    summary="List available languages for text-to-speech",
    response_model=List[LanguageOption],
)
def supported_langs(
    tts_manager: Annotated["TTSService", Depends(deps.get_tts_service)],
):
    """
    List supported languages.
    """
    return tts_manager.available_languages()
