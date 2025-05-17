import asyncio
import os
import sys
import time
from os import path
from typing import TYPE_CHECKING, List, Optional, Union

from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.music import MusicPlayerError
from app.schemas.music import MusicPlayerMode
from app.services.media.music_file_service import FileDetail

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService

original_stdout = sys.stdout
try:
    sys.stdout = open(os.devnull, "w")
    import pygame
finally:
    sys.stdout.close()
    sys.stdout = original_stdout


class MusicService(metaclass=SingletonMeta):
    """
    A singleton service to manage music playback and playlists.

    The `MusicService` handles functionalities such as:
        - Loading and updating playlists.
        - Controlling playback (play, pause, stop, next/prev track).
        - Configuring playback modes (single track, loop, queue).
        - Broadcasting the player state to connected clients.
    """

    def __init__(
        self,
        connection_manager: "ConnectionService",
        tracks: List[FileDetail],
        mode: MusicPlayerMode,
        music_dir: str,
        default_music_dir: str,
    ):
        """
        Initializes the MusicService with required file and connection services.
        """

        self.logger = Logger(__name__)
        self.default_music_dir = default_music_dir
        self.music_dir = music_dir
        self.connection_manager = connection_manager
        self.playlist: List[str] = [item.path for item in tracks]
        self.details = {item.path: item for item in tracks}
        self.track = (
            self.playlist[0] if len(self.playlist) > 0 else None
        )  # current track
        self.duration: float = (
            0.0 if self.track is None else self.get_track_duration(self.track)
        )  # total duration of current track in seconds
        self.mode: MusicPlayerMode = mode
        self.position = 0  # position in seconds
        self.is_playing = False
        self.last_update_time = time.time()
        self.stop_event = asyncio.Event()
        self.play_task: Optional[asyncio.Task] = None
        self.pygame = pygame

    def get_current_position(self) -> Union[int, float]:
        """
        Calculates and returns the current playback position of the active track.

        Returns:
            float: The current playback position in seconds.
        """

        if self.is_playing:
            self.position += time.time() - self.last_update_time
        self.last_update_time = time.time()
        return self.position

    def get_music_directory(self, filename: str) -> str:
        """
        Retrieves the directory of a specified music file.

        Args:
            filename: Name of the music file.

        Raises:
            FileNotFoundError: If the file doesn't exist.

        Returns:
            str: Directory path of the music file.
        """

        user_file = path.join(self.music_dir, filename)
        if path.exists(user_file):
            return self.music_dir
        elif path.exists(path.join(self.default_music_dir, filename)):
            return self.default_music_dir
        else:
            self.logger.error("The file '%s' was not found", user_file)
            raise FileNotFoundError("File not found")

    def get_track_duration(self, track: str) -> float:
        """
        Retrieves the duration of a specified music track.

        Args:
            track (str): The name of the track.

        Returns:
            float: The duration of the track in seconds.
        """

        file_detail = self.details.get(track)
        duration = file_detail.duration if file_detail else None

        return duration or 0.0

    def music_track_to_absolute(self, track: str) -> str:
        """
        Converts a music track's name to its absolute file path.

        Args:
            track (str): The name of the music track.

        Returns:
            str: The absolute file path of the track.
        """

        dir = self.get_music_directory(track)
        return path.join(dir, track)

    async def cancel_broadcast_task(self) -> None:
        """
        Cancels the currently running broadcast task, if active.

        This method unsets the stop event and ensures proper cleanup after
        the task cancellation.
        """

        if self.play_task:
            self.logger.info("Cancelling music player task")
            try:
                self.stop_event.set()
                self.play_task.cancel()
                await self.play_task
            except asyncio.CancelledError:
                self.logger.info("Music player task was cancelled")
                self.play_task = None
            finally:
                self.stop_event.clear()
        else:
            self.logger.info("Skipping cancelling music player task")

    @property
    def current_state(self):
        """
        Returns key metrics of the current state as a dictionary.

        The state includes details such as the currently playing track, playback position,
        playback mode, and whether or not music is playing.
        """
        return {
            "track": self.track,
            "position": round(self.get_current_position()),
            "is_playing": self.is_playing,
            "duration": self.duration,
            "mode": self.mode,
        }

    async def broadcast_state(self) -> None:
        """
        Broadcasts the current player state to all connected clients.

        The state includes details such as the currently playing track, playback position,
        playback mode, and whether or not music is playing.
        """
        await self.connection_manager.broadcast_json(
            {"type": "player", "payload": self.current_state}
        )

    def update_tracks(self, files_details: List[FileDetail]) -> None:
        """
        Updates the playlist with a new track order.

        Args:
            files_details: The new list of tracks.

        Behavior:
            If the currently playing track is removed from the playlist,
            playback will stop or advance to the next available track.
        """
        new_tracks = [item.path for item in files_details]
        details = {item.path: item for item in files_details}
        self.logger.debug("new_tracks=%s", new_tracks)

        track = self.track
        if track is not None and not track in new_tracks:
            self.next_track()
            if self.track == track and self.is_playing:
                self.stop_playing()
                self.track = new_tracks[0] if len(new_tracks) > 0 else None
        elif not self.is_playing:
            self.track = new_tracks[0] if len(new_tracks) > 0 else None
            self.position = 0

        self.playlist = new_tracks
        self.details = details
        if self.track:
            self.duration = self.get_track_duration(self.track)

    def start_broadcast_task(self) -> None:
        """
        Starts a background task to periodically broadcast the player state.
        """
        self.play_task = asyncio.create_task(self.broadcast_loop())

    def pygame_mixer_ensure(self):
        """
        Ensures the pygame mixer is initialized properly.

        This method reinitializes the mixer in case it is not already initialized,
        to avoid errors during playback operations.
        """
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    def toggle_playing(self) -> None:
        """
        Toggles playback (play or pause) for the current track.

        Raises:
            If no music track is loaded.
        """
        self.pygame_mixer_ensure()
        if self.is_playing:
            self.pygame.mixer.music.pause()
        else:
            if not self.pygame.mixer.music.get_busy():
                if self.track is None:
                    raise MusicPlayerError("No music track.")
                file_path = self.music_track_to_absolute(self.track)
                try:
                    self.pygame.mixer.music.load(file_path)
                    self.pygame.mixer.music.play(start=self.position)
                except (ValueError, RuntimeError, SystemError) as e:
                    raise MusicPlayerError(f"{e}")
            else:
                self.pygame.mixer.music.unpause()

        self.is_playing = not self.is_playing

    def stop_playing(self) -> None:
        """
        Stops playback and resets the playback position to the beginning.

        This method halts playback of the current track, resets the position to 0,
        and updates the playback state to indicate that no music is currently playing.
        """
        if self.is_playing:
            self.pygame_mixer_ensure()
            self.pygame.mixer.music.stop()
            self.is_playing = False
        self.position = 0

    def update_position(self, position: float) -> None:
        """
        Updates the current playback position of the currently playing track.

        Args:
            position (float): The position in seconds to set for the playback.

        Behavior:
            If a track is playing, the playback will seek to the specified position.
            Otherwise, the position is simply updated.
        """
        self.position = position
        if self.is_playing and self.track:
            self.pygame_mixer_ensure()
            self.pygame.mixer.music.set_pos(self.position)

    def update_mode(self, mode: MusicPlayerMode) -> None:
        """
        Updates the playback mode of the music player.

        Args:
            mode (MusicPlayerMode): The desired playback mode (e.g., LOOP, SINGLE, QUEUE).
        """
        self.mode = mode

    def play_track(self, track: str) -> None:
        """
        Plays a specified track from the playlist.

        Args:
            track (str): The name of the track to be played.

        Behavior:
            The current playback is stopped, the specified track is loaded,
            and playback starts from the beginning of the track.
        """
        self.stop_playing()

        self.track = track
        self.position = 0
        self.duration = self.get_track_duration(self.track)
        self.start_playing_current_track()

    def next_track(self) -> None:
        """
        Switches to the next track in the playlist.

        Behavior:
            If the current track is the last one in the playlist, the playback will loop
            back to the first track (if the mode allows). If the mode is QUEUE and
            the end of the queue is reached, playback will stop.
        """
        if not self.playlist:
            return
        current_index = (
            self.playlist.index(self.track) if self.track in self.playlist else -1
        )
        next_index = (current_index + 1) % len(
            self.playlist
        )  # Wrap around to the first track
        self.track = self.playlist[next_index]
        self.position = 0
        self.duration = self.get_track_duration(self.track)

        if self.is_playing:
            self.start_playing_current_track()

    def prev_track(self) -> None:
        """
        Switches to the previous track in the playlist.

        Behavior:
            If the current track is the first one in the playlist, the playback will loop
            back to the last track (if the mode allows).
        """
        if not self.playlist:
            return
        current_index = (
            self.playlist.index(self.track) if self.track in self.playlist else -1
        )
        prev_index = (current_index - 1) % len(
            self.playlist
        )  # Wrap around to the last track
        self.track = self.playlist[prev_index]
        self.position = 0
        self.duration = self.get_track_duration(self.track)

        if self.is_playing:
            self.start_playing_current_track()

    def start_playing_current_track(self) -> None:
        """
        Starts playback of the current track from the beginning.

        Behavior:
            If no track is loaded, a `MusicPlayerError` is raised. The current track is loaded
            and playback starts from the very beginning of the track.

        Raises:
            MusicPlayerError: If no music track is currently selected.
        """
        if self.track is None:
            raise MusicPlayerError("No music track.")

        file_path = self.music_track_to_absolute(self.track)
        self.pygame_mixer_ensure()
        try:
            self.pygame.mixer.music.load(file_path)
        except ValueError as e:
            raise MusicPlayerError(f"{e}")
        self.pygame.mixer.music.play()
        self.position = 0
        self.is_playing = True

    async def broadcast_loop(self) -> None:
        """
        Asynchronous loop to handle continuous broadcasting of the player state.

        Behavior:
            This loop periodically sends the player state (track, position, playback mode,
            etc.) to all connected clients. It also monitors the playback state and takes
            actions such as advancing to the next track if the current one ends.

        Loop Behavior:
            - If a loop mode is enabled, the playback mode dictates whether the
              same track restarts, the playlist advances, or playback stops.
            - The loop terminates if a `stop_event` is triggered.

        Raises:
            asyncio.CancelledError: If the loop is canceled while running.
        """
        while not self.stop_event.is_set():
            if self.is_playing:
                curr_pos = self.get_current_position()
                is_the_end = curr_pos + 0.100 >= self.duration
                if is_the_end:
                    if self.mode == MusicPlayerMode.LOOP_ONE:
                        self.start_playing_current_track()
                    elif self.mode == MusicPlayerMode.SINGLE:
                        self.is_playing = False
                        self.position = 0
                    elif self.mode in (MusicPlayerMode.LOOP, MusicPlayerMode.QUEUE):
                        self.next_track()
                        if (
                            self.mode == MusicPlayerMode.QUEUE
                            and self.track == self.playlist[0]
                            and not self.is_playing
                        ):
                            self.is_playing = False
                            break

            # Broadcast player state to clients
            await self.broadcast_state()
            await asyncio.sleep(0.5)

    async def cleanup(self):
        """
        Shuts down the music service and ensures proper cleanup of resources.
        """
        if self.is_playing:
            try:
                self.logger.info("Stopping playing music")
                self.pygame.mixer.music.stop()
            except Exception:
                self.logger.error("Failed to stop music", exc_info=True)

        await self.cancel_broadcast_task()
