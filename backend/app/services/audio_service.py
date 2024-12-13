import os
import re
import subprocess
from typing import Union

from app.exceptions.audio import AmixerNotInstalled, AudioVolumeError
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from pydub import AudioSegment

debug = os.getenv("PX_LOG_LEVEL", "INFO").upper() == "DEBUG"


class AudioService(metaclass=SingletonMeta):
    """
    Service to handle audio playback volume adjustments and interactions with audio files.

    This class is responsible for interacting with the system's `amixer` tool to
    retrieve and modify the playback device's volume level.
    """

    def __init__(self):
        self.logger = Logger(__name__)

    def get_audio_duration(self, filename: str):
        """
        Get the duration of an audio file in seconds.
        """
        audio = AudioSegment.from_file(filename)
        secs = len(audio) / 1000.0
        return secs

    def get_volume(self):
        """
        Retrieves the current playback volume level.

        This method uses the `amixer` tool to fetch the volume of the "Master" device.

        Returns:
        --------------
        - `int`: The current volume as a percentage.

        Raises:
        --------------
        - `AmixerNotInstalled`: If `amixer` is not installed on the system.
        - `AudioVolumeError`: If an error occurs while retrieving the volume.
        """
        try:
            result = subprocess.run(
                ["amixer", "get", "Master"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT if not debug else subprocess.DEVNULL,
            )

            output = result.stdout.decode("utf-8")

            match = re.search(r"\[(\d+%)\]", output)

            if match:
                return int(match.group(1).rstrip("%"))
            else:
                return "Volume information not found"
        except FileNotFoundError:
            self.logger.warning("'amixer' is not installed on your system.")
            raise AmixerNotInstalled("'amixer' is not installed on the system!")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Amixer error:", e)
            raise AudioVolumeError("Error getting the volume") from e

    def set_volume(self, volume_percentage: Union[int, float]):
        """
        Sets the playback volume to the specified level.

        This method uses the `amixer` tool to adjust the volume of the "Master" device.

        Args:
        --------------
        - `volume_percentage` (int | float): Target volume (0 to 100).

        Raises:
        --------------
        - `AmixerNotInstalled`: If `amixer` is not installed on the system.
        - `AudioVolumeError`: If an error occurs while setting the volume.
        """
        volume_percentage = int(max(0, min(100, volume_percentage)))
        try:
            subprocess.run(
                ["amixer", "sset", "Master", f"{volume_percentage}%"],
                check=True,
                stdout=subprocess.PIPE if not debug else subprocess.DEVNULL,
                stderr=subprocess.STDOUT if not debug else subprocess.DEVNULL,
            )

        except FileNotFoundError:
            self.logger.warning("'amixer' is not installed on your system.")
            raise AmixerNotInstalled("'amixer' is not installed on the system!")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Amixer error:", e)
            raise AudioVolumeError("Amixer error") from e
