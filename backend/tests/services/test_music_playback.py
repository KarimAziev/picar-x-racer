import unittest
from collections.abc import Generator

from app.exceptions.music import MusicInitError, MusicPlayerError
from app.services.media.music_playback import (
    MiniaudioMusicPlayback,
    PlaybackDevice,
    PlaybackStream,
)


def make_stream(*chunks: bytes) -> PlaybackStream:
    def generate() -> Generator[bytes, int, None]:
        requested_frames = yield b""
        for chunk in chunks:
            requested_frames = yield chunk
        _ = requested_frames

    stream = generate()
    next(stream)
    return stream


def make_failing_stream(error: Exception) -> PlaybackStream:
    def generate() -> Generator[bytes, int, None]:
        _ = yield b""
        raise error

    stream = generate()
    next(stream)
    return stream


class FakePlaybackDevice:
    def __init__(self) -> None:
        self.started_streams: list[PlaybackStream] = []
        self.current_stream: PlaybackStream | None = None
        self.stop_count = 0
        self.close_count = 0

    def start(self, callback_generator: PlaybackStream) -> None:
        self.started_streams.append(callback_generator)
        self.current_stream = callback_generator

    def stop(self) -> None:
        self.stop_count += 1
        self.current_stream = None

    def close(self) -> None:
        self.close_count += 1
        self.current_stream = None

    def request_frames(self, frame_count: int = 128) -> object:
        if self.current_stream is None:
            raise AssertionError("No stream is currently playing")
        return self.current_stream.send(frame_count)


class FailingStartDevice(FakePlaybackDevice):
    def start(self, callback_generator: PlaybackStream) -> None:
        super().start(callback_generator)
        raise RuntimeError("start failed")


class TestMiniaudioMusicPlayback(unittest.TestCase):
    def setUp(self) -> None:
        self.device = FakePlaybackDevice()
        self.stream_calls: list[tuple[str, int]] = []

        def stream_factory(file_path: str, seek_frame: int) -> PlaybackStream:
            self.stream_calls.append((file_path, seek_frame))
            return make_stream(b"first", b"second")

        self.player = MiniaudioMusicPlayback(
            device_factory=lambda: self.device,
            stream_factory=stream_factory,
        )

    def test_device_is_created_lazily_and_seek_uses_pcm_frames(self) -> None:
        created = 0

        def device_factory() -> PlaybackDevice:
            nonlocal created
            created += 1
            return self.device

        player = MiniaudioMusicPlayback(
            sample_rate=48_000,
            device_factory=device_factory,
            stream_factory=lambda _path, _seek: make_stream(b"audio"),
        )

        self.assertEqual(created, 0)

        player.play("/music/song.mp3", position=1.25)

        self.assertEqual(created, 1)
        self.assertEqual(len(self.device.started_streams), 1)

    def test_play_passes_requested_position_to_stream_factory(self) -> None:
        self.player.play("/music/song.mp3", position=1.25)

        self.assertEqual(
            self.stream_calls,
            [("/music/song.mp3", 55_125)],
        )

    def test_pause_and_resume_reuse_the_same_decoder_stream(self) -> None:
        self.player.play("/music/song.mp3")
        original_stream = self.device.started_streams[0]

        self.player.pause()
        self.assertTrue(self.player.can_resume)

        self.player.resume()

        self.assertFalse(self.player.can_resume)
        self.assertIs(self.device.started_streams[1], original_stream)

    def test_natural_completion_produces_one_event(self) -> None:
        self.player.play("/music/song.mp3")

        self.device.request_frames()
        self.device.request_frames()
        with self.assertRaises(StopIteration):
            self.device.request_frames()

        event = self.player.take_event()
        self.assertIsNotNone(event)
        self.assertIsNone(event.error if event else None)
        self.assertIsNone(self.player.take_event())

    def test_decoder_failure_is_reported_as_completion_event(self) -> None:
        error = RuntimeError("decode failed")
        player = MiniaudioMusicPlayback(
            device_factory=lambda: self.device,
            stream_factory=lambda _path, _seek: make_failing_stream(error),
        )
        player.play("/music/broken.mp3")

        with self.assertRaises(StopIteration):
            self.device.request_frames()

        event = player.take_event()
        self.assertIs(event.error if event else None, error)

    def test_device_initialization_failure_is_domain_error(self) -> None:
        player = MiniaudioMusicPlayback(
            device_factory=lambda: (_ for _ in ()).throw(RuntimeError("no device")),
            stream_factory=lambda _path, _seek: make_stream(b"audio"),
        )

        with self.assertRaisesRegex(MusicInitError, "no device"):
            player.play("/music/song.mp3")

    def test_stream_initialization_failure_is_domain_error(self) -> None:
        player = MiniaudioMusicPlayback(
            device_factory=lambda: self.device,
            stream_factory=lambda _path, _seek: (_ for _ in ()).throw(
                RuntimeError("bad file")
            ),
        )

        with self.assertRaisesRegex(MusicPlayerError, "bad file"):
            player.play("/music/broken.mp3")

    def test_failed_device_start_resets_device_callback(self) -> None:
        device = FailingStartDevice()
        player = MiniaudioMusicPlayback(
            device_factory=lambda: device,
            stream_factory=lambda _path, _seek: make_stream(b"audio"),
        )

        with self.assertRaisesRegex(MusicPlayerError, "start failed"):
            player.play("/music/song.mp3")

        self.assertEqual(device.stop_count, 1)
        self.assertIsNone(device.current_stream)

    def test_stop_discards_paused_stream_and_completion_event(self) -> None:
        self.player.play("/music/song.mp3")
        self.player.pause()

        self.player.stop()

        self.assertFalse(self.player.can_resume)
        self.assertIsNone(self.player.take_event())

    def test_close_is_idempotent(self) -> None:
        self.player.play("/music/song.mp3")

        self.player.close()
        self.player.close()

        self.assertEqual(self.device.close_count, 1)


if __name__ == "__main__":
    unittest.main()
