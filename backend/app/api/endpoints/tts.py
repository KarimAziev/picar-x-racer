"""
Endpoints related to text to speech functionalities.
"""

import asyncio
from typing import TYPE_CHECKING, List

from app.api.deps import get_tts_manager
from app.exceptions.tts import TextToSpeechException
from app.schemas.tts import LanguageOption, TextToSpeechData
from app.core.logger import Logger
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.tts_service import TTSService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/tts/speak",
    summary="Speak the given text using Google Translate TTS API",
    responses={
        400: {
            "description": "Bad Request. If the text-to-speech is already running.",
            "content": {
                "application/json": {"example": {"detail": "Already speaking"}}
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
    tts_manager: "TTSService" = Depends(get_tts_manager),
):
    """
    Endpoint to convert text to speech.

    Returns:
    -------------
    **None**: The endpoint does not return any data to the caller.

    All connected clients are notified asynchronously via WebSocket.
    """
    logger.info("TTS payload=%s", payload)
    try:
        connection_manager: "ConnectionService" = request.app.state.app_manager
        text = payload.text
        lang = payload.lang or "en"
        await asyncio.to_thread(tts_manager.text_to_speech, text, lang)
        await connection_manager.broadcast_json(
            {"type": "info", "payload": "Speaking: " + text}
        )
    except TextToSpeechException as err:
        logger.error("Text to speech error: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error("Unexpected text to speech error.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to speak the text")


@router.get(
    "/tts/languages",
    summary="List available languages for text-to-speech",
    response_model=List[LanguageOption],
)
def supported_langs(
    tts_manager: "TTSService" = Depends(get_tts_manager),
):
    """
    List supported languages.
    """
    return tts_manager.available_languages()
