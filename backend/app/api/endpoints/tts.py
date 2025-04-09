"""
Endpoints related to text to speech functionalities.
"""

import asyncio
from typing import TYPE_CHECKING, Annotated, List

from app.api import deps
from app.core.logger import Logger
from app.exceptions.tts import TextToSpeechException
from app.schemas.common import Message
from app.schemas.tts import LanguageOption, TextToSpeechData
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.media.tts_service import TTSService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/tts/speak",
    summary="Speak the given text using Google Translate TTS API",
    response_description="Message with the spoken text.",
    response_model=Message,
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
    tts_manager: Annotated["TTSService", Depends(deps.get_tts_service)],
):
    """
    Endpoint to convert text to speech.

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
        return {"message": text}
    except TextToSpeechException as err:
        logger.error("Text to speech error: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error("Unexpected text to speech error.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to speak the text")


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
