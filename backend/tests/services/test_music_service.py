import tempfile
import unittest
from collections import deque
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock

from app.schemas.file_filter import FileDetail
from app.schemas.music import MusicPlayerMode
from app.services.connection_service import ConnectionService
from app.services.media.music_playback import PlaybackEvent
from app.services.media.music_service import MusicService


class FakeMusicPlayback:
    def __init__(self) -> None:
        self.can_resume = False
        self.calls: list[tuple[object, ...]] = []
        self.events: deque[PlaybackEvent] = deque()
        self.play_error: Exception | None = None

    def play(self, file_path: str, position: float = 0.0) -> None:
        self.calls.append(("play", file_path, position))
        if self.play_error is not None:
            raise self.play_error
        self.can_resume = False

    def pause(self) -> None:
        self.calls.append(("pause",))
        self.can_resume = True

    def resume(self) -> None:
        self.calls.append(("resume",))
        self.can_resume = False

    def stop(self) -> None:
        self.calls.append(("stop",))
        self.can_resume = False
        self.events.clear()

    def take_event(self) -> PlaybackEvent | None:
        return self.events.popleft() if self.events else None

    def close(self) -> None:
        self.calls.append(("close",))


def track(name: str, duration: float = 10.0) -> FileDetail:
    return FileDetail(
        name=name,
        path=name,
        size=1,
        is_dir=False,
        modified=1.0,
        type="audio",
        content_type="audio/mpeg",
        duration=duration,
    )


class TestMusicService(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.music_dir = Path(self.temp_dir.name)
        for name in ("one.mp3", "two.mp3"):
            (self.music_dir / name).touch()

        self.connection_mock = AsyncMock(spec=ConnectionService)
        self.playback = FakeMusicPlayback()
        self.service = MusicService(
            connection_manager=cast(ConnectionService, self.connection_mock),
            tracks=[track("one.mp3"), track("two.mp3")],
            mode=MusicPlayerMode.LOOP,
            music_dir=str(self.music_dir),
            default_music_dir=str(self.music_dir),
            playback=self.playback,
        )

    def test_toggle_starts_pauses_and_resumes_current_track(self) -> None:
        self.service.toggle_playing()
        self.service.toggle_playing()
        self.service.toggle_playing()

        self.assertEqual(
            self.playback.calls,
            [
                ("play", str(self.music_dir / "one.mp3"), 0.0),
                ("pause",),
                ("resume",),
            ],
        )
        self.assertTrue(self.service.is_playing)

    def test_stop_also_discards_a_paused_stream(self) -> None:
        self.service.toggle_playing()
        self.service.toggle_playing()

        self.service.stop_playing()

        self.assertEqual(self.playback.calls[-1], ("stop",))
        self.assertFalse(self.service.is_playing)
        self.assertEqual(self.service.position, 0.0)

    def test_seek_restarts_active_decoder_at_requested_position(self) -> None:
        self.service.toggle_playing()

        self.service.update_position(4.5)

        self.assertEqual(
            self.playback.calls[-1],
            ("play", str(self.music_dir / "one.mp3"), 4.5),
        )
        self.assertEqual(self.service.position, 4.5)

    def test_seek_is_clamped_to_known_duration(self) -> None:
        self.service.update_position(50)

        self.assertEqual(self.service.position, 10.0)

    def test_next_track_replaces_active_playback(self) -> None:
        self.service.toggle_playing()

        self.service.next_track()

        self.assertEqual(self.service.track, "two.mp3")
        self.assertEqual(
            self.playback.calls[-1],
            ("play", str(self.music_dir / "two.mp3"), 0.0),
        )

    def test_replacement_failure_clears_playing_state(self) -> None:
        self.service.toggle_playing()
        self.playback.play_error = RuntimeError("start failed")

        with self.assertRaisesRegex(RuntimeError, "start failed"):
            self.service.next_track()

        self.assertFalse(self.service.is_playing)

    def test_queue_stops_after_the_last_track(self) -> None:
        self.service.mode = MusicPlayerMode.QUEUE
        self.service.play_track("two.mp3")

        self.service._process_playback_event(PlaybackEvent())

        self.assertEqual(self.service.track, "two.mp3")
        self.assertFalse(self.service.is_playing)
        self.assertEqual(self.playback.calls[-1], ("stop",))

    def test_loop_advances_and_wraps_playlist(self) -> None:
        self.service.play_track("two.mp3")

        self.service._process_playback_event(PlaybackEvent())

        self.assertEqual(self.service.track, "one.mp3")
        self.assertTrue(self.service.is_playing)
        self.assertEqual(
            self.playback.calls[-1],
            ("play", str(self.music_dir / "one.mp3"), 0.0),
        )

    def test_loop_one_restarts_current_track(self) -> None:
        self.service.mode = MusicPlayerMode.LOOP_ONE
        self.service.play_track("one.mp3")

        self.service._process_playback_event(PlaybackEvent())

        self.assertEqual(self.service.track, "one.mp3")
        self.assertEqual(
            self.playback.calls[-1],
            ("play", str(self.music_dir / "one.mp3"), 0.0),
        )

    def test_decoder_failure_stops_instead_of_repeating_track(self) -> None:
        self.service.toggle_playing()

        self.service._process_playback_event(
            PlaybackEvent(error=RuntimeError("decode failed"))
        )

        self.assertFalse(self.service.is_playing)
        self.assertEqual(self.playback.calls[-1], ("stop",))

    async def test_cleanup_keeps_backend_reusable_but_close_releases_it(self) -> None:
        self.service.toggle_playing()

        await self.service.cleanup()

        self.assertNotIn(("close",), self.playback.calls)

        await self.service.close()

        self.assertEqual(self.playback.calls[-1], ("close",))


if __name__ == "__main__":
    unittest.main()
