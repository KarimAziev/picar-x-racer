import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI

from app.api.deps import LifespanAppDeps
from app.main_server import lifespan


class TestMainLifespanCleanup(unittest.IsolatedAsyncioTestCase):
    async def test_camera_stops_before_detection_even_when_media_cleanup_fails(
        self,
    ) -> None:
        for failure in (None, RuntimeError("audio failed"), asyncio.CancelledError()):
            with self.subTest(failure=failure):
                events: list[str] = []

                def stop_camera() -> None:
                    events.append("camera")

                def close_tts() -> None:
                    events.append("tts")
                    if failure is not None:
                        raise failure

                async def stop_detection() -> None:
                    events.append("detection")

                camera = MagicMock(shutdown=MagicMock(side_effect=stop_camera))
                detection = MagicMock(cleanup=AsyncMock(side_effect=stop_detection))
                music = MagicMock()
                music.music_service.close = AsyncMock()
                values = MagicMock(spec=dict)
                values.get.side_effect = {
                    "camera_manager": camera,
                    "connection_manager": MagicMock(),
                    "detection_manager": detection,
                    "music_file_service": music,
                    "tts_service": MagicMock(close=MagicMock(side_effect=close_tts)),
                }.get

                @asynccontextmanager
                async def dependencies(app: FastAPI) -> AsyncIterator[LifespanAppDeps]:
                    yield values

                with (
                    patch(
                        "app.util.solve_lifespan.solve_lifespan",
                        return_value=dependencies,
                    ),
                    patch("app.main_server.signal.signal"),
                    patch("app.main_server.get_ip_address", return_value="127.0.0.1"),
                    patch("app.main_server.print_initial_message"),
                    patch.dict("os.environ", {"PX_APP_MODE": "production"}),
                ):
                    if isinstance(failure, asyncio.CancelledError):
                        with self.assertRaises(asyncio.CancelledError):
                            async with lifespan(FastAPI()):
                                pass
                    else:
                        async with lifespan(FastAPI()):
                            pass
                self.assertEqual(events, ["camera", "tts", "detection"])
                music.music_service.close.assert_awaited_once()
