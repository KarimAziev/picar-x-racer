"""Low-level, interruptible music playback backed by Miniaudio."""

from __future__ import annotations

import threading
from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Any, Protocol

import miniaudio

from app.core.logger import Logger
from app.exceptions.music import MusicInitError, MusicPlayerError

_log = Logger(__name__)

PlaybackStream = Generator[Any, int, None]
DeviceFactory = Callable[[], "PlaybackDevice"]
StreamFactory = Callable[[str, int], PlaybackStream]


class PlaybackDevice(Protocol):
    """Subset of :class:`miniaudio.PlaybackDevice` used by the player."""

    def start(self, callback_generator: PlaybackStream) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class PlaybackEvent:
    """A completed stream, optionally carrying a decoder failure."""

    error: Exception | None = None


class MusicPlayback(Protocol):
    """Playback operations required by :class:`MusicService`."""

    @property
    def can_resume(self) -> bool: ...

    def play(self, file_path: str, position: float = 0.0) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...

    def take_event(self) -> PlaybackEvent | None: ...

    def close(self) -> None: ...


class MiniaudioMusicPlayback:
    """Stream local music through one lazily-created Miniaudio output device."""

    def __init__(
        self,
        *,
        sample_rate: int = 44_100,
        channels: int = 2,
        buffer_size_msec: int = 200,
        device_factory: DeviceFactory | None = None,
        stream_factory: StreamFactory | None = None,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")
        if channels not in (1, 2):
            raise ValueError("channels must be 1 or 2")
        if buffer_size_msec <= 0:
            raise ValueError("buffer_size_msec must be greater than zero")

        self._sample_rate = sample_rate
        self._channels = channels
        self._buffer_size_msec = buffer_size_msec
        self._device_factory = device_factory or self._create_device
        self._stream_factory = stream_factory or self._create_source_stream
        self._device: PlaybackDevice | None = None
        self._source_stream: PlaybackStream | None = None
        self._playback_stream: PlaybackStream | None = None
        self._can_resume = False
        self._closed = False
        self._generation = 0
        self._event: PlaybackEvent | None = None
        self._lock = threading.RLock()
        self._event_lock = threading.Lock()

    @property
    def can_resume(self) -> bool:
        """Return whether a paused stream can resume without being recreated."""
        with self._lock:
            return self._can_resume

    def play(self, file_path: str, position: float = 0.0) -> None:
        """Start a file at the requested position, replacing the previous stream."""
        if position < 0:
            raise MusicPlayerError("Playback position cannot be negative")

        with self._lock:
            self._ensure_open()
            self._stop_locked()
            device = self._ensure_device()
            seek_frame = round(position * self._sample_rate)
            generation = self._generation

            try:
                source_stream = self._stream_factory(file_path, seek_frame)
                playback_stream = self._with_completion_event(
                    source_stream,
                    generation,
                )
                next(playback_stream)
                self._source_stream = source_stream
                self._playback_stream = playback_stream
                device.start(playback_stream)
            except Exception as error:
                self._generation += 1
                try:
                    device.stop()
                except Exception:
                    _log.warning(
                        "Unable to reset the audio output after a failed start",
                        exc_info=True,
                    )
                self._close_streams_locked()
                raise MusicPlayerError(
                    f"Unable to play the audio file: {error}"
                ) from error

            self._can_resume = False
            _log.info(
                "Music playback started: position=%.3fs",
                position,
            )

    def pause(self) -> None:
        """Pause the current stream while retaining its decoder position."""
        with self._lock:
            if self._playback_stream is None or self._can_resume:
                return
            try:
                if self._device is not None:
                    self._device.stop()
            except Exception as error:
                raise MusicPlayerError(f"Unable to pause playback: {error}") from error
            self._can_resume = True

    def resume(self) -> None:
        """Resume a previously paused stream."""
        with self._lock:
            self._ensure_open()
            if not self._can_resume or self._playback_stream is None:
                raise MusicPlayerError("No paused music stream to resume")
            device = self._ensure_device()
            try:
                device.start(self._playback_stream)
            except Exception as error:
                try:
                    device.stop()
                except Exception:
                    _log.warning(
                        "Unable to reset the audio output after a failed resume",
                        exc_info=True,
                    )
                raise MusicPlayerError(f"Unable to resume playback: {error}") from error
            self._can_resume = False

    def stop(self) -> None:
        """Stop playback and discard the current decoder stream."""
        with self._lock:
            self._stop_locked()

    def take_event(self) -> PlaybackEvent | None:
        """Return and clear the latest natural-completion or decoder event."""
        with self._event_lock:
            event = self._event
            self._event = None
            return event

    def close(self) -> None:
        """Stop playback and release the Miniaudio output device."""
        with self._lock:
            if self._closed:
                return

            stop_error: Exception | None = None
            try:
                self._stop_locked()
            except Exception as error:
                stop_error = error

            device = self._device
            self._device = None
            self._closed = True
            if device is not None:
                try:
                    device.close()
                except Exception as error:
                    if stop_error is None:
                        stop_error = error

            if stop_error is not None:
                raise MusicPlayerError(
                    f"Unable to close the audio output: {stop_error}"
                ) from stop_error

    def _create_device(self) -> PlaybackDevice:
        return miniaudio.PlaybackDevice(
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=self._channels,
            sample_rate=self._sample_rate,
            buffersize_msec=self._buffer_size_msec,
            app_name="PiCar-X Racer",
        )

    def _create_source_stream(
        self,
        file_path: str,
        seek_frame: int,
    ) -> PlaybackStream:
        return miniaudio.stream_file(
            file_path,
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=self._channels,
            sample_rate=self._sample_rate,
            seek_frame=seek_frame,
        )

    def _ensure_device(self) -> PlaybackDevice:
        if self._device is None:
            try:
                self._device = self._device_factory()
            except Exception as error:
                raise MusicInitError(
                    f"Unable to initialize the audio output: {error}"
                ) from error
        return self._device

    def _ensure_open(self) -> None:
        if self._closed:
            raise MusicInitError("Music playback is closed")

    def _stop_locked(self) -> None:
        self._generation += 1
        self._clear_event()
        stop_error: Exception | None = None
        if self._device is not None:
            try:
                self._device.stop()
            except Exception as error:
                stop_error = error

        self._close_streams_locked()
        self._can_resume = False
        if stop_error is not None:
            raise MusicPlayerError(
                f"Unable to stop playback: {stop_error}"
            ) from stop_error

    def _close_streams_locked(self) -> None:
        playback_stream = self._playback_stream
        source_stream = self._source_stream
        self._playback_stream = None
        self._source_stream = None

        if playback_stream is not None:
            try:
                playback_stream.close()
            except Exception:
                _log.warning("Unable to close the music playback stream", exc_info=True)

        if source_stream is not None:
            try:
                source_stream.close()
            except Exception:
                _log.warning("Unable to close the music decoder stream", exc_info=True)

    def _with_completion_event(
        self,
        source_stream: PlaybackStream,
        generation: int,
    ) -> PlaybackStream:
        requested_frames = yield b""
        try:
            while True:
                samples = source_stream.send(requested_frames)
                requested_frames = yield samples
        except StopIteration:
            self._set_event(generation, PlaybackEvent())
        except GeneratorExit:
            raise
        except Exception as error:
            self._set_event(generation, PlaybackEvent(error=error))

    def _set_event(self, generation: int, event: PlaybackEvent) -> None:
        with self._event_lock:
            if generation == self._generation:
                self._event = event

    def _clear_event(self) -> None:
        with self._event_lock:
            self._event = None
