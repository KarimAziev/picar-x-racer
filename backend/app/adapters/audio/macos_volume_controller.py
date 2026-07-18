import subprocess

from app.exceptions.audio import AudioVolumeError, AudioVolumeUnavailable

_COMMAND_TIMEOUT_SECONDS = 5


class MacOSVolumeController:
    """Controls the macOS system output volume through ``osascript``."""

    def get_volume(self) -> int:
        result = self._run(
            ["osascript", "-e", "output volume of (get volume settings)"]
        )
        try:
            volume = int(result.stdout.strip())
        except ValueError as error:
            raise AudioVolumeError(
                "Invalid volume information returned by osascript."
            ) from error

        if not 0 <= volume <= 100:
            raise AudioVolumeError("Invalid volume returned by osascript.")
        return volume

    def set_volume(self, volume: int) -> None:
        self._run(["osascript", "-e", f"set volume output volume {volume}"])

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
                "macOS volume control is unavailable because 'osascript' was not found."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise AudioVolumeError("The osascript command timed out.") from error
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() if error.stderr else "no error output"
            raise AudioVolumeError(
                f"The osascript command failed: {detail}."
            ) from error
