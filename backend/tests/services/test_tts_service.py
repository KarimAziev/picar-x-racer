import unittest
from typing import cast
from unittest.mock import Mock

from app.exceptions.tts import TextToSpeechRequestError, TextToSpeechUnavailable
from app.services.media.tts_service import TTSService
from gspeech import GSpeechError, SpeechHandle, SpeechPlayer, SpeechPolicy


class TestTTSService(unittest.TestCase):
    def setUp(self) -> None:
        self.player_mock = Mock(spec=SpeechPlayer)
        self.handle_mock = Mock(spec=SpeechHandle)
        self.handle_mock.id = "request-id"
        self.handle_mock.lang = "uk"
        self.handle_mock.text = "Привіт"
        self.player_mock.speak.return_value = self.handle_mock
        self.service = TTSService(cast(SpeechPlayer, self.player_mock))

    def test_speak_submits_with_replace_policy(self) -> None:
        handle = self.service.speak("Привіт", "uk")

        self.assertIs(handle, self.handle_mock)
        self.player_mock.speak.assert_called_once_with(
            "Привіт",
            "uk",
            policy=SpeechPolicy.REPLACE,
        )

    def test_text_to_speech_preserves_the_previous_service_entry_point(self) -> None:
        handle = self.service.text_to_speech("Привіт", "uk")

        self.assertIs(handle, self.handle_mock)
        self.player_mock.speak.assert_called_once_with(
            "Привіт",
            "uk",
            policy=SpeechPolicy.REPLACE,
        )

    def test_invalid_request_is_exposed_as_application_error(self) -> None:
        self.player_mock.speak.side_effect = ValueError("Unsupported language")

        with self.assertRaisesRegex(
            TextToSpeechRequestError,
            "Unsupported language",
        ):
            self.service.speak("Hello", "invalid")

    def test_unavailable_player_is_exposed_as_application_error(self) -> None:
        self.player_mock.speak.side_effect = GSpeechError("Player is closed")

        with self.assertRaisesRegex(
            TextToSpeechUnavailable,
            "Player is closed",
        ):
            self.service.speak("Hello")

    def test_stop_delegates_wait_options(self) -> None:
        self.player_mock.stop.return_value = True

        stopped = self.service.stop(wait=True, timeout=2.0)

        self.assertTrue(stopped)
        self.player_mock.stop.assert_called_once_with(wait=True, timeout=2.0)

    def test_close_releases_the_player(self) -> None:
        self.service.close(timeout=2.0)

        self.player_mock.close.assert_called_once_with(timeout=2.0)


if __name__ == "__main__":
    unittest.main()
