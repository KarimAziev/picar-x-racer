"""Playlist and player-state management for local music playback."""

from __future__ import annotations

import asyncio
import threading
import time
from os import path
from typing import TYPE_CHECKING, Any

from app.core.logger import Logger
from app.exceptions.music import MusicPlayerError
from app.schemas.file_filter import FileDetail
from app.schemas.music import MusicPlayerMode
from app.services.media.music_playback import (
    MiniaudioMusicPlayback,
    MusicPlayback,
    PlaybackEvent,
)

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService

_log = Logger(__name__)


class MusicService:
    """Manage a playlist and delegate audio output to an interruptible player."""

    def __init__(
        self,
        connection_manager: ConnectionService,
        tracks: list[FileDetail],
        mode: MusicPlayerMode,
        music_dir: str,
        default_music_dir: str,
        playback: MusicPlayback | None = None,
    ) -> None:
        self.default_music_dir = default_music_dir
        self.music_dir = music_dir
        self.connection_manager = connection_manager
        self.playlist = [item.path for item in tracks]
        self.details = {item.path: item for item in tracks}
        self.track = self.playlist[0] if self.playlist else None
        self.duration = (
            0.0 if self.track is None else self.get_track_duration(self.track)
        )
        self.mode = mode
        self.position = 0.0
        self.is_playing = False
        self.last_update_time = time.monotonic()
        self.stop_event = asyncio.Event()
        self.play_task: asyncio.Task[None] | None = None
        self._playback = playback if playback is not None else MiniaudioMusicPlayback()
        self._state_lock = threading.RLock()

    def get_current_position(self) -> float:
        """Return the current playback position in seconds."""
        with self._state_lock:
            now = time.monotonic()
            if self.is_playing:
                self.position += max(0.0, now - self.last_update_time)
                if self.duration > 0:
                    self.position = min(self.position, self.duration)
            self.last_update_time = now
            return self.position

    def get_music_directory(self, filename: str) -> str:
        """Return the user or bundled directory containing a music file."""
        user_file = path.join(self.music_dir, filename)
        if path.exists(user_file):
            return self.music_dir

        default_file = path.join(self.default_music_dir, filename)
        if path.exists(default_file):
            return self.default_music_dir

        _log.error("The music file '%s' was not found", user_file)
        raise FileNotFoundError("File not found")

    def get_track_duration(self, track: str) -> float:
        """Return cached duration metadata for a track."""
        file_detail = self.details.get(track)
        return file_detail.duration or 0.0 if file_detail else 0.0

    def music_track_to_absolute(self, track: str) -> str:
        """Resolve a playlist track to an absolute file path."""
        directory = self.get_music_directory(track)
        return path.join(directory, track)

    async def cancel_broadcast_task(self) -> None:
        """Cancel the periodic state broadcaster if it is running."""
        task = self.play_task
        if task is None:
            _log.info("Skipping cancellation of the music player task")
            return

        _log.info("Cancelling music player task")
        self.stop_event.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            _log.info("Music player task was cancelled")
        except Exception:
            _log.error("Music player task failed during cleanup", exc_info=True)
        finally:
            self.play_task = None
            self.stop_event.clear()

    @property
    def current_state(self) -> dict[str, Any]:
        """Return the state serialized by the music API and WebSocket."""
        with self._state_lock:
            return {
                "track": self.track,
                "position": round(self.get_current_position()),
                "is_playing": self.is_playing,
                "duration": self.duration,
                "mode": self.mode,
            }

    async def broadcast_state(self) -> None:
        """Broadcast the current player state to all connected clients."""
        await self.connection_manager.broadcast_json(
            {"type": "player", "payload": self.current_state}
        )

    def update_tracks(self, files_details: list[FileDetail]) -> None:
        """Replace playlist metadata while preserving a valid current track."""
        with self._state_lock:
            new_tracks = [item.path for item in files_details]
            self.playlist = new_tracks
            self.details = {item.path: item for item in files_details}
            _log.debug("Updated music playlist: tracks=%d", len(new_tracks))

            if self.track not in new_tracks:
                was_playing = self.is_playing
                self._playback.stop()
                self.is_playing = False
                self.track = new_tracks[0] if new_tracks else None
                self.position = 0.0
                self.duration = (
                    self.get_track_duration(self.track) if self.track else 0.0
                )
                if was_playing and self.track is not None:
                    self._start_playing_current_track()
            elif self.track is not None:
                self.duration = self.get_track_duration(self.track)

            self.last_update_time = time.monotonic()

    def start_broadcast_task(self) -> None:
        """Start periodic player-state broadcasts once."""
        if self.play_task is not None and not self.play_task.done():
            return
        self.play_task = asyncio.create_task(self.broadcast_loop())

    def toggle_playing(self) -> None:
        """Pause active playback or resume/start the selected track."""
        with self._state_lock:
            if self.is_playing:
                self.get_current_position()
                self._playback.pause()
                self.is_playing = False
                return

            if self.track is None:
                raise MusicPlayerError("No music track.")

            if self._playback.can_resume:
                self._playback.resume()
            else:
                file_path = self.music_track_to_absolute(self.track)
                self._playback.play(file_path, self.position)

            self.last_update_time = time.monotonic()
            self.is_playing = True

    def stop_playing(self) -> None:
        """Stop playback and reset the selected track to its beginning."""
        with self._state_lock:
            self._playback.stop()
            self.is_playing = False
            self.position = 0.0
            self.last_update_time = time.monotonic()

    def update_position(self, position: float) -> None:
        """Seek active playback or set the next resume/start position."""
        with self._state_lock:
            next_position = max(0.0, position)
            if self.duration > 0:
                next_position = min(next_position, self.duration)
            self.position = next_position

            if self.is_playing and self.track is not None:
                file_path = self.music_track_to_absolute(self.track)
                self.is_playing = False
                self._playback.play(file_path, self.position)
                self.is_playing = True
            elif self._playback.can_resume:
                self._playback.stop()

            self.last_update_time = time.monotonic()

    def update_mode(self, mode: MusicPlayerMode) -> None:
        """Set the playlist completion policy."""
        with self._state_lock:
            self.mode = mode

    def play_track(self, track: str) -> None:
        """Select and immediately play a track from its beginning."""
        with self._state_lock:
            self._playback.stop()
            self.is_playing = False
            self.track = track
            self.position = 0.0
            self.duration = self.get_track_duration(track)
            self._start_playing_current_track()

    def next_track(self) -> None:
        """Select the next track, preserving the current play/pause state."""
        with self._state_lock:
            if not self.playlist:
                return
            was_playing = self.is_playing
            current_index = (
                self.playlist.index(self.track) if self.track in self.playlist else -1
            )
            self._select_track((current_index + 1) % len(self.playlist))
            if was_playing:
                self._start_playing_current_track()
            else:
                self._playback.stop()

    def prev_track(self) -> None:
        """Select the previous track, preserving the current play/pause state."""
        with self._state_lock:
            if not self.playlist:
                return
            was_playing = self.is_playing
            current_index = (
                self.playlist.index(self.track) if self.track in self.playlist else -1
            )
            self._select_track((current_index - 1) % len(self.playlist))
            if was_playing:
                self._start_playing_current_track()
            else:
                self._playback.stop()

    def start_playing_current_track(self) -> None:
        """Start the selected track from its beginning."""
        with self._state_lock:
            self._start_playing_current_track()

    def _start_playing_current_track(self) -> None:
        if self.track is None:
            raise MusicPlayerError("No music track.")

        file_path = self.music_track_to_absolute(self.track)
        self.is_playing = False
        self._playback.play(file_path)
        self.position = 0.0
        self.last_update_time = time.monotonic()
        self.is_playing = True

    def _select_track(self, index: int) -> None:
        self.track = self.playlist[index]
        self.position = 0.0
        self.duration = self.get_track_duration(self.track)
        self.last_update_time = time.monotonic()

    def _process_playback_event(self, event: PlaybackEvent) -> None:
        with self._state_lock:
            if not self.is_playing:
                return

            if event.error is not None:
                _log.error(
                    "Music stream failed: track=%s error=%s",
                    self.track,
                    type(event.error).__name__,
                )
                self._playback.stop()
                self.is_playing = False
                self.position = 0.0
                return

            if self.mode == MusicPlayerMode.LOOP_ONE:
                self._start_playing_current_track()
                return

            if self.mode == MusicPlayerMode.SINGLE:
                self.stop_playing()
                return

            if not self.playlist or self.track not in self.playlist:
                self.stop_playing()
                return

            current_index = self.playlist.index(self.track)
            if (
                self.mode == MusicPlayerMode.QUEUE
                and current_index == len(self.playlist) - 1
            ):
                self.stop_playing()
                return

            self._select_track((current_index + 1) % len(self.playlist))
            self._start_playing_current_track()

    async def broadcast_loop(self) -> None:
        """Broadcast state and apply playlist policy after stream completion."""
        while not self.stop_event.is_set():
            event = self._playback.take_event()
            if event is not None:
                self._process_playback_event(event)
            await self.broadcast_state()
            await asyncio.sleep(0.5)

    async def cleanup(self) -> None:
        """Stop music and the broadcaster while keeping the device reusable."""
        try:
            await asyncio.to_thread(self.stop_playing)
        except Exception:
            _log.error("Failed to stop music", exc_info=True)
        await self.cancel_broadcast_task()

    async def close(self) -> None:
        """Permanently stop the service and release its audio output."""
        await self.cleanup()
        await asyncio.to_thread(self._playback.close)
