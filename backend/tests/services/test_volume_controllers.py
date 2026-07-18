import subprocess
import unittest
from unittest.mock import patch

from app.adapters.audio.alsa_volume_controller import AlsaVolumeController
from app.adapters.audio.macos_volume_controller import MacOSVolumeController
from app.exceptions.audio import AudioVolumeError, AudioVolumeUnavailable


class TestAlsaVolumeController(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = AlsaVolumeController()

    @patch("app.adapters.audio.alsa_volume_controller.subprocess.run")
    def test_get_volume_parses_amixer_output(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Mono: Playback 42 [42%] [-20.00dB] [on]\n",
            stderr="",
        )

        self.assertEqual(self.controller.get_volume(), 42)
        run.assert_called_once_with(
            ["amixer", "get", "Master"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("app.adapters.audio.alsa_volume_controller.subprocess.run")
    def test_set_volume_uses_percentage_argument(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        self.controller.set_volume(73)

        run.assert_called_once_with(
            ["amixer", "sset", "Master", "73%"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("app.adapters.audio.alsa_volume_controller.subprocess.run")
    def test_get_volume_rejects_unrecognized_output(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="unrecognized", stderr=""
        )

        with self.assertRaisesRegex(AudioVolumeError, "not found"):
            self.controller.get_volume()

    @patch("app.adapters.audio.alsa_volume_controller.subprocess.run")
    def test_missing_amixer_is_reported_as_unavailable(self, run) -> None:
        run.side_effect = FileNotFoundError

        with self.assertRaisesRegex(AudioVolumeUnavailable, "amixer"):
            self.controller.get_volume()

    @patch("app.adapters.audio.alsa_volume_controller.subprocess.run")
    def test_command_failure_preserves_stderr_in_error(self, run) -> None:
        run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["amixer"],
            stderr="Unable to find simple control 'Master'",
        )

        with self.assertRaisesRegex(AudioVolumeError, "Unable to find simple control"):
            self.controller.get_volume()

    @patch("app.adapters.audio.alsa_volume_controller.subprocess.run")
    def test_command_timeout_is_reported_as_volume_error(self, run) -> None:
        run.side_effect = subprocess.TimeoutExpired(cmd=["amixer"], timeout=5)

        with self.assertRaisesRegex(AudioVolumeError, "timed out"):
            self.controller.get_volume()


class TestMacOSVolumeController(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = MacOSVolumeController()

    @patch("app.adapters.audio.macos_volume_controller.subprocess.run")
    def test_get_volume_parses_osascript_output(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=" 58\n", stderr=""
        )

        self.assertEqual(self.controller.get_volume(), 58)
        run.assert_called_once_with(
            ["osascript", "-e", "output volume of (get volume settings)"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("app.adapters.audio.macos_volume_controller.subprocess.run")
    def test_set_volume_uses_validated_integer_in_script(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        self.controller.set_volume(64)

        run.assert_called_once_with(
            ["osascript", "-e", "set volume output volume 64"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("app.adapters.audio.macos_volume_controller.subprocess.run")
    def test_get_volume_rejects_non_numeric_output(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="unknown", stderr=""
        )

        with self.assertRaisesRegex(AudioVolumeError, "Invalid volume information"):
            self.controller.get_volume()

    @patch("app.adapters.audio.macos_volume_controller.subprocess.run")
    def test_get_volume_rejects_out_of_range_output(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="101", stderr=""
        )

        with self.assertRaisesRegex(AudioVolumeError, "Invalid volume"):
            self.controller.get_volume()


if __name__ == "__main__":
    unittest.main()
