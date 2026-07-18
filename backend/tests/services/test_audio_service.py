import unittest
from typing import cast
from unittest.mock import Mock

from app.services.media.audio_metadata_service import AudioMetadataService
from app.services.media.audio_service import AudioService


class FakeVolumeController:
    def __init__(self, volume: int = 50) -> None:
        self.volume = volume
        self.set_calls: list[int] = []

    def get_volume(self) -> int:
        return self.volume

    def set_volume(self, volume: int) -> None:
        self.volume = volume
        self.set_calls.append(volume)


class TestAudioService(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = FakeVolumeController(37)
        self.metadata_mock = Mock(spec=AudioMetadataService)
        self.metadata_service = cast(AudioMetadataService, self.metadata_mock)
        self.service = AudioService(self.controller, self.metadata_service)

    def test_get_volume_delegates_to_controller(self) -> None:
        self.assertEqual(self.service.get_volume(), 37)

    def test_set_volume_normalizes_and_delegates(self) -> None:
        self.service.set_volume(125)
        self.service.set_volume(-4)
        self.service.set_volume(42.9)

        self.assertEqual(self.controller.set_calls, [100, 0, 42])

    def test_get_audio_duration_delegates_to_metadata_service(self) -> None:
        self.metadata_mock.get_duration.return_value = 12.5

        self.assertEqual(self.service.get_audio_duration("track.mp3"), 12.5)
        self.metadata_mock.get_duration.assert_called_once_with("track.mp3")


if __name__ == "__main__":
    unittest.main()
