"""
A module for playing music, sound effects, and controlling musical notes.

- Play sound effects and music files.
- Generate and play musical notes.
- Control musical parameters like tempo, time signature, and key signature.

"""

import math
import struct
import threading
import time
from typing import Optional

import pyaudio
import pygame
from pydub import AudioSegment


class Music:
    """
    A class for playing music, sound effects, and controlling musical notes.

    ### Key Features:
    - Play sound effects and music files.
    - Generate and play musical notes.
    - Control musical parameters like tempo, time signature, and key signature.

    ### Attributes:
        - `FORMAT` (int): Audio format for PyAudio.
        - `CHANNELS` (int): Number of audio channels (default is 1, mono).
        - `RATE` (int): Sample rate (default is 44100 Hz).
        - Various constants for musical keys and note durations.

    ### Methods:
        - `__init__(self)`: Initialize the music system using pygame.
        - `time_signature(self, top: Optional[int], bottom: Optional[int])`: Set or get the time signature.
        - `key_signature(self, key: Optional[int])`: Set or get the key signature.
        - `tempo(self, tempo: Optional[float], note_value=QUARTER_NOTE)`: Set or get the tempo.
        - `beat(self, beat)`: Calculate the beat delay in seconds.
        - `note(self, note, natural=False)`: Get the frequency of a note.
        - `sound_play(self, filename, volume=None)`: Play a sound effect.
        - `sound_play_threading(self, filename, volume=None)`: Play a sound effect in a separate thread.
        - `music_play(self, filename, loops=1, start=0.0, volume=None)`: Play a music file.
        - `music_set_volume(self, value)`: Set the music volume.
        - `music_get_volume(self)`: Get the music volume.
        - `music_stop(self)`: Stop the music.
        - `music_pause(self)`: Pause the music.
        - `music_resume(self)`: Resume the music.
        - `music_unpause(self)`: Unpause the music (resume playing).
        - `music_get_duration(self, filename)`: Get the duration of music filename.
        - `sound_length(self, filename)`: Get the length of a sound effect file.
        - `get_tone_data(self, freq: float, duration: float)`: Generate tone data for a given frequency and duration.
        - `play_tone_for(self, freq, duration)`: Play a tone for a specified duration.

    #### Musical Terms:
    - **Tempo**: The speed of the music, measured in beats per minute (BPM).
    - **Note**: A specific pitch in music, identified by its frequency.
    - **Frequency**: The number of sound waves per second, measured in Hertz (Hz). Higher frequencies correspond to higher pitches.
    - **Duration**: The length of time a note is held.
    - **Key Signature**: Indicates the key of a piece of music, using sharps or flats.

    Example:

    ```python
    # Initialize the Music class
    music = Music()

    # Play a sound effect
    music.sound_play("path_to_sound.wav")

    # Set and get tempo
    music.tempo(120)

    # Play a musical note
    freq = music.note("C4")
    music.play_tone_for(freq, 1)  # Play C4 for 1 second
    ```
    """

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    KEY_G_MAJOR = 1
    KEY_D_MAJOR = 2
    KEY_A_MAJOR = 3
    KEY_E_MAJOR = 4
    KEY_B_MAJOR = 5
    KEY_F_SHARP_MAJOR = 6
    KEY_C_SHARP_MAJOR = 7

    KEY_F_MAJOR = -1
    KEY_B_FLAT_MAJOR = -2
    KEY_E_FLAT_MAJOR = -3
    KEY_A_FLAT_MAJOR = -4
    KEY_D_FLAT_MAJOR = -5
    KEY_G_FLAT_MAJOR = -6
    KEY_C_FLAT_MAJOR = -7

    KEY_SIGNATURE_SHARP = 1
    KEY_SIGNATURE_FLAT = -1

    WHOLE_NOTE = 1
    HALF_NOTE = 1 / 2
    QUARTER_NOTE = 1 / 4
    EIGHTH_NOTE = 1 / 8
    SIXTEENTH_NOTE = 1 / 16

    NOTE_BASE_FREQ = 440
    """Base note frequency for calculation (A4)"""
    NOTE_BASE_INDEX = 69
    """Base note index for calculation (A4) MIDI compatible"""

    NOTES = [
        # List of musical notes corresponding to MIDI note numbers
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "A0",
        "A#0",
        "B0",
        "C1",
        "C#1",
        "D1",
        "D#1",
        "E1",
        "F1",
        "F#1",
        "G1",
        "G#1",
        "A1",
        "A#1",
        "B1",
        "C2",
        "C#2",
        "D2",
        "D#2",
        "E2",
        "F2",
        "F#2",
        "G2",
        "G#2",
        "A2",
        "A#2",
        "B2",
        "C3",
        "C#3",
        "D3",
        "D#3",
        "E3",
        "F3",
        "F#3",
        "G3",
        "G#3",
        "A3",
        "A#3",
        "B3",
        "C4",
        "C#4",
        "D4",
        "D#4",
        "E4",
        "F4",
        "F#4",
        "G4",
        "G#4",
        "A4",
        "A#4",
        "B4",
        "C5",
        "C#5",
        "D5",
        "D#5",
        "E5",
        "F5",
        "F#5",
        "G5",
        "G#5",
        "A5",
        "A#5",
        "B5",
        "C6",
        "C#6",
        "D6",
        "D#6",
        "E6",
        "F6",
        "F#6",
        "G6",
        "G#6",
        "A6",
        "A#6",
        "B6",
        "C7",
        "C#7",
        "D7",
        "D#7",
        "E7",
        "F7",
        "F#7",
        "G7",
        "G#7",
        "A7",
        "A#7",
        "B7",
        "C8",
    ]
    """Notes name, MIDI compatible"""

    def __init__(self):
        """Initialize music"""
        self.pygame = pygame
        self.pygame.mixer.init()
        self.time_signature(4, 4)
        self.tempo(120, 1 / 4)
        self.key_signature(0)

    def time_signature(self, top: Optional[int] = None, bottom: Optional[int] = None):
        """
        Set or get the time signature.

        The time signature is a musical notation denoting the number of beats in a measure and the note value that gets one beat.

        Args:
            top (Optional[int]): The top number of the time signature (e.g., 4 in 4/4 time).
            bottom (Optional[int]): The bottom number of the time signature (e.g., 4 in 4/4 time).

        Returns:
            tuple: The current time signature (top, bottom).
        """
        if top is None and bottom is None:
            return self._time_signature
        if bottom is None:
            bottom = top
        self._time_signature = (top, bottom)
        return self._time_signature

    def key_signature(self, key: Optional[int] = None):
        """
        Set or get the key signature.

        The key signature indicates the key of the music, using sharp (#) or flat (b) symbols.

        Args:
            key (Optional[int/str]): The key signature, which can be an integer (use KEY_XX_MAJOR) or a string ("#", "bb", etc.).

        Returns:
            int: The current key signature as an integer.
        """
        if key is None:
            return self._key_signature
        if isinstance(key, str):
            if "#" in key:
                key = len(key) * self.KEY_SIGNATURE_SHARP
            elif "b" in key:
                key = len(key) * self.KEY_SIGNATURE_FLAT
        self._key_signature = key
        return self._key_signature

    def tempo(self, tempo: Optional[float] = None, note_value=QUARTER_NOTE):
        """
        Set or get the tempo in beats per minute (BPM).

        Args:
            tempo (Optional[float]): The tempo in BPM.
            note_value (float): The note value for the tempo (default is QUARTER_NOTE).

        Returns:
            tuple: The current tempo (bpm, note_value).
        """
        if tempo is None and note_value is None:
            return self._tempo
        if tempo is not None:
            try:
                self._tempo = (tempo, note_value)
                self.beat_unit = 60.0 / tempo
                return self._tempo
            except:
                raise ValueError(f"Tempo must be int not {tempo}")

    def beat(self, beat):
        """
        Calculate the beat delay in seconds from the tempo.

        Args:
            beat (float): The beat index.

        Returns:
            float: The beat delay in seconds.
        """
        beat = beat / self._tempo[1] * self.beat_unit
        return beat

    def note(self, note, natural=False):
        """
        Get the frequency of a musical note.

        Args:
            note (str/int): The note name (e.g., "C4"). See NOTES for reference.
            natural (bool): Whether the note should be considered natural (no sharps or flats).

        Returns:
            float: The frequency of the note in Hertz (Hz).
        """
        if isinstance(note, str):
            if note in self.NOTES:
                note = self.NOTES.index(note)
            else:
                raise ValueError(f"Note {note} not found, note must be in Music.NOTES")
        if not natural:
            note += self.key_signature()
            note = min(max(note, 0), len(self.NOTES) - 1)
        note_delta = note - self.NOTE_BASE_INDEX
        freq = self.NOTE_BASE_FREQ * (2 ** (note_delta / 12))
        return freq

    def sound_play(self, filename, volume=None):
        """
        Play a sound effect file.

        Args:
            filename (str): The sound effect file name.
            volume (Optional[int]): The volume level (0-100). If not provided, the default volume is used.

        Returns:
            None
        """
        sound = self.pygame.mixer.Sound(filename)
        if volume is not None:
            # Attention:
            # The volume of sound and music is separate,
            # and the volume of different sound objects is also separate.
            sound.set_volume(round(volume / 100.0, 2))
        time_delay = round(sound.get_length(), 2)
        sound.play()
        time.sleep(time_delay)

    def sound_play_threading(self, filename, volume=None):
        """
        Play a sound effect in a separate thread.

        Args:
            filename (str): The sound effect file name.
            volume (Optional[int]): The volume level (0-100). If not provided, the default volume is used.

        Returns:
            None
        """
        obj = threading.Thread(
            target=self.sound_play, kwargs={"filename": filename, "volume": volume}
        )
        obj.start()

    def music_play(self, filename: str, loops=1, start=0.0, volume=None):
        """
        Play a music file.

        Args:
            filename (str): The music file name.
            loops (int): Number of loops (0: loop forever, 1: play once, 2: play twice, ...).
            start (float): Start time in seconds.
            volume (Optional[int]): The volume level (0-100). If not provided, the default volume is used.

        Returns:
            None
        """
        if volume is not None:
            self.music_set_volume(volume)
        self.pygame.mixer.music.load(filename)
        self.pygame.mixer.music.play(loops, start)

    def music_get_volume(self):
        """
        Get the music volume level (0-100).
        """
        value = round(self.pygame.mixer.music.get_volume() * 100.0, 2)
        return value

    def music_set_volume(self, value):
        """
        Set the music volume.

        Args:
            value (int): The volume level (0-100).

        Returns:
            None
        """
        value = round(value / 100.0, 2)
        self.pygame.mixer.music.set_volume(value)

    def music_stop(self):
        """
        Stop the music.

        Returns:
            None
        """
        self.pygame.mixer.music.stop()

    def music_pause(self):
        """
        Pause the music.

        Returns:
            None
        """
        self.pygame.mixer.music.pause()

    def music_resume(self):
        """
        Resume the music.

        Returns:
            None
        """
        self.pygame.mixer.music.unpause()

    def music_unpause(self):
        """
        Unpause the music (resume playing).

        Returns:
            None
        """
        self.pygame.mixer.music.unpause()

    def music_get_duration(self, filename: str):
        """
        Get the duration of an audio file in seconds.
        """
        audio = AudioSegment.from_file(filename)
        secs = len(audio) / 1000.0
        return secs

    def sound_length(self, filename):
        """
        Get the length of a sound effect file in seconds.

        Args:
            filename (str): The sound effect file name.

        Returns:
            float: The length of the sound effect in seconds.
        """
        music = self.pygame.mixer.Sound(str(filename))
        return round(music.get_length(), 2)

    def get_tone_data(self, freq: float, duration: float):
        """
        Generate tone data for a given frequency and duration.

        Args:
            freq (float): The frequency of the tone.
            duration (float): The duration of the tone in seconds.

        Returns:
            bytes: The tone data as bytes.

        Credit to: Aditya Shankar & Gringo Suave (https://stackoverflow.com/a/53231212/14827323)
        """
        duration /= 2.0
        frame_count = int(self.RATE * duration)

        remainder_frames = frame_count % self.RATE
        wavedata = []

        for i in range(frame_count):
            a = self.RATE / freq  # number of frames per wave
            b = i / a
            c = b * (2 * math.pi)
            d = math.sin(c) * 32767
            e = int(d)
            wavedata.append(e)

        for i in range(remainder_frames):
            wavedata.append(0)

        number_of_bytes = str(len(wavedata))
        wavedata = struct.pack(number_of_bytes + "h", *wavedata)

        return wavedata

    def play_tone_for(self, freq, duration):
        """
        Play a tone for a specified duration.

        Args:
            freq (float): The frequency of the tone. You can use NOTES to get the frequency.
            duration (float): The duration of the tone in seconds.

        Returns:
            None

        Credit to: Aditya Shankar & Gringo Suave (https://stackoverflow.com/a/53231212/14827323)
        """
        p = pyaudio.PyAudio()
        frames = self.get_tone_data(freq, duration)
        stream = p.open(
            format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE, output=True
        )
        stream.write(frames)
