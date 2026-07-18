import unittest

from app.adapters.audio.alsa_volume_controller import AlsaVolumeController
from app.adapters.audio.factory import create_volume_controller
from app.adapters.audio.macos_volume_controller import MacOSVolumeController
from app.exceptions.audio import AudioVolumeUnavailable, AudioVolumeUnsupported


class TestVolumeControllerFactory(unittest.TestCase):
    def test_selects_macos_controller_when_osascript_exists(self) -> None:
        controller = create_volume_controller("Darwin", lambda command: f"/{command}")

        self.assertIsInstance(controller, MacOSVolumeController)

    def test_selects_alsa_controller_when_amixer_exists(self) -> None:
        controller = create_volume_controller("Linux", lambda command: f"/{command}")

        self.assertIsInstance(controller, AlsaVolumeController)

    def test_missing_platform_command_is_reported_as_unavailable(self) -> None:
        controller = create_volume_controller("Linux", lambda command: None)

        with self.assertRaisesRegex(AudioVolumeUnavailable, "amixer"):
            controller.get_volume()

    def test_unknown_platform_is_reported_as_unsupported(self) -> None:
        controller = create_volume_controller("Plan9", lambda command: None)

        with self.assertRaisesRegex(AudioVolumeUnsupported, "Plan9"):
            controller.set_volume(50)


if __name__ == "__main__":
    unittest.main()
