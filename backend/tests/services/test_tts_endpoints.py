import unittest
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

from app.api.endpoints.tts import stop_text_to_speech, text_to_speech
from app.exceptions.tts import TextToSpeechRequestError, TextToSpeechUnavailable
from app.schemas.tts import TextToSpeechData
from app.services.connection_service import ConnectionService
from app.services.media.tts_service import TTSService
from fastapi import HTTPException, Request


class TestTTSEndpoints(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.connection_mock = AsyncMock(spec=ConnectionService)
        state = SimpleNamespace(app_manager=self.connection_mock)
        self.request = cast(
            Request,
            SimpleNamespace(app=SimpleNamespace(state=state)),
        )
        self.tts_mock = Mock(spec=TTSService)
        self.tts_service = cast(TTSService, self.tts_mock)

    async def test_speak_submits_and_broadcasts_without_waiting(self) -> None:
        response = await text_to_speech(
            self.request,
            TextToSpeechData(text="Hello", lang="en"),
            self.tts_service,
        )

        self.assertEqual(response, {"message": "Hello"})
        self.tts_mock.speak.assert_called_once_with("Hello", "en")
        self.connection_mock.broadcast_json.assert_awaited_once_with(
            {"type": "info", "payload": "Speaking: Hello"}
        )

    async def test_speak_defaults_to_english(self) -> None:
        await text_to_speech(
            self.request,
            TextToSpeechData(text="Hello", lang=None),
            self.tts_service,
        )

        self.tts_mock.speak.assert_called_once_with("Hello", "en")

    async def test_invalid_speech_request_maps_to_400(self) -> None:
        self.tts_mock.speak.side_effect = TextToSpeechRequestError("invalid")

        with self.assertRaises(HTTPException) as context:
            await text_to_speech(
                self.request,
                TextToSpeechData(text="Hello", lang="invalid"),
                self.tts_service,
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "invalid")
        self.connection_mock.broadcast_json.assert_not_awaited()

    async def test_unavailable_player_maps_to_503(self) -> None:
        self.tts_mock.speak.side_effect = TextToSpeechUnavailable("closed")

        with self.assertRaises(HTTPException) as context:
            await text_to_speech(
                self.request,
                TextToSpeechData(text="Hello", lang=None),
                self.tts_service,
            )

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.detail, "closed")

    async def test_broadcast_failure_does_not_reject_accepted_speech(self) -> None:
        self.connection_mock.broadcast_json.side_effect = RuntimeError("disconnected")

        response = await text_to_speech(
            self.request,
            TextToSpeechData(text="Hello", lang=None),
            self.tts_service,
        )

        self.assertEqual(response, {"message": "Hello"})

    async def test_stop_interrupts_and_broadcasts(self) -> None:
        self.tts_mock.stop.return_value = True

        response = await stop_text_to_speech(self.request, self.tts_service)

        self.assertEqual(response, {"message": "Speech stopped"})
        self.tts_mock.stop.assert_called_once_with(wait=True, timeout=5.0)
        self.connection_mock.broadcast_json.assert_awaited_once_with(
            {"type": "info", "payload": "Speech stopped"}
        )

    async def test_stop_is_idempotent_when_speech_is_inactive(self) -> None:
        self.tts_mock.stop.return_value = False

        response = await stop_text_to_speech(self.request, self.tts_service)

        self.assertEqual(response, {"message": "No speech was active"})
        self.connection_mock.broadcast_json.assert_not_awaited()

    async def test_stop_timeout_maps_to_503(self) -> None:
        self.tts_mock.stop.side_effect = TimeoutError

        with self.assertRaises(HTTPException) as context:
            await stop_text_to_speech(self.request, self.tts_service)

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(
            context.exception.detail,
            "Text-to-speech player did not stop in time",
        )


if __name__ == "__main__":
    unittest.main()
