from typing import TYPE_CHECKING

from app.api.deps import get_tts_manager
from app.exceptions.tts import TextToSpeechException
from app.schemas.tts import TextToSpeechData
from app.util.logger import Logger
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.tts_service import TTSService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/api/tts/speak",
    summary="Text to Speech API Endpoint",
)
async def text_to_speech(
    request: Request,
    payload: TextToSpeechData,
    tts_manager: "TTSService" = Depends(get_tts_manager),
):
    """
    Endpoint to convert text to speech.

    Args:
    -------------
    - payload (TextToSpeechData): Contains the text and language details for text-to-speech conversion.
    - tts_manager (TTSService): The audio service for managing audio playback.

    Returns:
    -------------
    None: The endpoint does not return any data to the caller.
    All connected clients are notified asynchronously via WebSocket.

    Raises:
    -------------
    - HTTPException (400): If Google speech is not available.
    - HTTPException (500): If an unexpected error occurs.
    """
    try:
        connection_manager: "ConnectionService" = request.app.state.app_manager
        text = payload.text
        lang = payload.lang or "en"
        tts_manager.text_to_speech(text, lang)
        await connection_manager.broadcast_json(
            {"type": "info", "payload": "Speaking: " + text}
        )
    except TextToSpeechException as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Text to speech issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")
