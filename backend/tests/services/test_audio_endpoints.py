import unittest
from typing import cast

from app.api.endpoints.audio import get_volume
from app.exceptions.audio import (
    AudioVolumeError,
    AudioVolumeUnavailable,
    AudioVolumeUnsupported,
)
from app.services.media.audio_service import AudioService
from fastapi import HTTPException


class FailingAudioService:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def get_volume(self) -> int:
        raise self._error


class TestAudioEndpoints(unittest.IsolatedAsyncioTestCase):
    async def test_get_volume_maps_unsupported_platform_to_501(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await get_volume(
                cast(
                    AudioService,
                    FailingAudioService(AudioVolumeUnsupported("unsupported")),
                )
            )

        self.assertEqual(context.exception.status_code, 501)
        self.assertEqual(context.exception.detail, "unsupported")

    async def test_get_volume_maps_unavailable_backend_to_503(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await get_volume(
                cast(
                    AudioService,
                    FailingAudioService(AudioVolumeUnavailable("unavailable")),
                )
            )

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.detail, "unavailable")

    async def test_get_volume_maps_backend_failure_to_503(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await get_volume(
                cast(AudioService, FailingAudioService(AudioVolumeError("failed")))
            )

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.detail, "failed")


if __name__ == "__main__":
    unittest.main()
