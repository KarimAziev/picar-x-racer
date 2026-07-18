import re
import subprocess

from app.exceptions.audio import AudioVolumeError, AudioVolumeUnavailable

_COMMAND_TIMEOUT_SECONDS = 5
_VOLUME_PATTERN = re.compile(r"\[(\d{1,3})%\]")


class AlsaVolumeController:
    """Controls the ALSA Master playback volume through ``amixer``."""

    def get_volume(self) -> int:
        result = self._run(["amixer", "get", "Master"])
        match = _VOLUME_PATTERN.search(result.stdout)
        if match is None:
            raise AudioVolumeError("Volume information not found in amixer output.")

        volume = int(match.group(1))
        if not 0 <= volume <= 100:
            raise AudioVolumeError("Invalid volume returned by amixer.")
        return volume

    def set_volume(self, volume: int) -> None:
        self._run(["amixer", "sset", "Master", f"{volume}%"])

    @staticmethod
    def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=_COMMAND_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as error:
            raise AudioVolumeUnavailable(
                "ALSA volume control is unavailable because 'amixer' was not found."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise AudioVolumeError("The amixer command timed out.") from error
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() if error.stderr else "no error output"
            raise AudioVolumeError(f"The amixer command failed: {detail}.") from error
