import asyncio
import time
from os import path
from typing import TYPE_CHECKING, List, Optional

import pygame
from app.exceptions.music import MusicPlayerError
from app.schemas.music import MusicPlayerMode
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.files_service import FilesService


class MusicService(metaclass=SingletonMeta):
    """
    A singleton service to manage music playback and playlists.

    The `MusicService` handles functionalities such as:
        - Loading and updating playlists.
        - Controlling playback (play, pause, stop, next/prev track).
        - Configuring playback modes (single track, loop, queue).
        - Broadcasting the player state to connected clients.

    Attributes:
        logger (Logger): The logger instance to log messages.
        file_manager (FilesService): Service instance for managing files and directories.
        connection_manager (ConnectionService): Service instance for managing client connections.
        playlist (List[str]): Ordered list of music tracks in the playlist.
        track (Optional[str]): The currently playing track, if any.
        duration (float): The total duration of the current track in seconds.
        mode (MusicPlayerMode): The playback mode (e.g., LOOP, SINGLE, QUEUE).
        position (float): The current playback position of the active track in seconds.
        is_playing (bool): True if the music is currently playing, False otherwise.
        stop_event (asyncio.Event): Event to signal cancellation of broadcast tasks.
        play_task (Optional[asyncio.Task]): The currently running broadcast task.
        lock (asyncio.Event): Lock for managing asynchronous operations.
        pygame (pygame): The pygame library instance for music playback.
    """

    def __init__(
        self, file_manager: "FilesService", connection_manager: "ConnectionService"
    ):
        """
        Initializes the MusicService with required file and connection services.

        Args:
            file_manager (FilesService): The service responsible for file management.
            connection_manager (ConnectionService): The service responsible for managing client connections.
        """

        self.logger = Logger(__name__)
        self.file_manager = file_manager
        self.connection_manager = connection_manager
        self.playlist: List[str] = self.file_manager.list_music_tracks_sorted()
        self.track = (
            self.playlist[0] if len(self.playlist) > 0 else None
        )  # current track
        self.duration: float = (
            0.0 if self.track is None else self.get_track_duration(self.track)
        )  # total duration of current track in seconds
        self.mode: MusicPlayerMode = MusicPlayerMode.LOOP
        self.position = 0  # position in seconds
        self.is_playing = False
        self.last_update_time = time.time()
        self.stop_event = asyncio.Event()
        self.play_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Event()
        self.pygame = pygame
        self.pygame.mixer.init()

    def get_current_position(self):
        """
        Calculates and returns the current playback position of the active track.

        Returns:
            float: The current playback position in seconds.
        """

        if self.is_playing:
            self.position += time.time() - self.last_update_time
        self.last_update_time = time.time()
        return self.position

    def get_track_duration(self, track: str):
        """
        Retrieves the duration of a specified music track.

        Args:
            track (str): The name of the track.

        Returns:
            float: The duration of the track in seconds.
        """

        file_path = self.music_track_to_absolute(track)
        details = self.file_manager.get_audio_file_details(file_path)
        duration: float = details.get('duration', 0.0) if details else 0.0  # in seconds

        return duration

    def music_track_to_absolute(self, track: str):
        """
        Converts a music track's name to its absolute file path.

        Args:
            track (str): The name of the music track.

        Returns:
            str: The absolute file path of the track.
        """

        dir = self.file_manager.get_music_directory(track)
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

    async def broadcast_state(self):
        """
        Broadcasts the current player state to all connected clients.

        The state includes details such as the currently playing track, playback position,
        playback mode, and whether or not music is playing.
        """
        data = {
            "track": self.track,
            "position": self.get_current_position(),
            "is_playing": self.is_playing,
            "duration": self.duration,
            "mode": self.mode,
        }
        await self.connection_manager.broadcast_json(
            {"type": "player", "payload": data}
        )

    def remove_music_track(self, track: str):
        """
        Removes a music track from the playlist.

        Args:
            track (str): The name of the track to remove.

        Returns:
            bool: True if the track is successfully removed, False otherwise.

        Raises:
            MusicPlayerError: If the track to be removed is currently playing.
        """
        if self.track == track:
            self.next_track()
        if self.track == track:
            raise MusicPlayerError("Can't remove the playing track")

        return self.file_manager.remove_music(track)

    def update_tracks(self, new_tracks: List[str]):
        """
        Updates the playlist with a new track order.

        Args:
            new_tracks (List[str]): The new list of tracks.

        Behavior:
            If the currently playing track is removed from the playlist,
            playback will stop or advance to the next available track.
        """
        track = self.track
        if track is not None and not track in new_tracks:
            self.next_track()
            if self.track == track and self.is_playing:
                self.stop_playing()
                self.track = new_tracks[0] if len(new_tracks) > 0 else None

        self.playlist = new_tracks
        self.file_manager.save_custom_music_order(new_tracks)

    def start_broadcast_task(self):
        """
        Starts a background task to periodically broadcast the player state.
        """
        self.play_task = asyncio.create_task(self.broadcast_loop())

    def toggle_playing(self):
        """
        Toggles playback (play or pause) for the current track.

        Raises:
            MusicPlayerError: If no music track is loaded.
        """
        if self.is_playing:
            self.pygame.mixer.music.pause()
        else:
            if not self.pygame.mixer.music.get_busy():
                if self.track is None:
                    raise MusicPlayerError("No music track")
                file_path = self.music_track_to_absolute(self.track)
                self.pygame.mixer.music.load(file_path)
                self.pygame.mixer.music.play(start=self.position)
            else:
                self.pygame.mixer.music.unpause()

        self.is_playing = not self.is_playing

    def stop_playing(self):
        """
        Stops playback and resets the playback position to the beginning.

        This method halts playback of the current track, resets the position to 0,
        and updates the playback state to indicate that no music is currently playing.
        """
        if self.is_playing:
            self.pygame.mixer.music.stop()
        self.position = 0
        self.is_playing = not self.is_playing

    def update_position(self, position: float):
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
            self.pygame.mixer.music.set_pos(self.position)

    def update_mode(self, mode: MusicPlayerMode):
        """
        Updates the playback mode of the music player.

        Args:
            mode (MusicPlayerMode): The desired playback mode (e.g., LOOP, SINGLE, QUEUE).
        """
        self.mode = mode

    def play_track(self, track: str):
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

    def next_track(self):
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

    def prev_track(self):
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

    def start_playing_current_track(self):
        """
        Starts playback of the current track from the beginning.

        Behavior:
            If no track is loaded, a `MusicPlayerError` is raised. The current track is loaded
            and playback starts from the very beginning of the track.

        Raises:
            MusicPlayerError: If no music track is currently selected.
        """
        if self.track is None:
            raise MusicPlayerError("No music track")

        file_path = self.music_track_to_absolute(self.track)
        self.pygame.mixer.music.load(file_path)
        self.pygame.mixer.music.play()
        self.position = 0
        self.is_playing = True

    async def broadcast_loop(self):
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
                if self.pygame.mixer.music.get_busy() == 0:
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