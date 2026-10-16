import asyncio
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gpiozero import Device
from gpiozero.pins.mock import MockFactory

from app.schemas.robot.config import HardwareConfig
from app.managers.async_task_manager import AsyncTaskManager
from app.schemas.robot.motors import GPIODCMotorConfig
from app.schemas.robot.distance import UltrasonicConfig
from app.services.sensors.distance_service import DistanceService
from app.services.sensors.led_service import LEDService
from app.util.gpio_reservations import validate_led_pin


class TestGPIOProcessSafety(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        data = json.loads(
            (Path(__file__).resolve().parents[3] / "config.json").read_text()
        )
        self.config = HardwareConfig.model_validate(data)
        self.config.motors = [
            GPIODCMotorConfig(
                name="Drive",
                forward_pin="GPIO20",
                backward_pin="GPIO21",
                enable_pin="GPIO26",
            )
        ]
        self.manager = MagicMock()
        self.manager.load_data.return_value = self.config.model_dump(mode="json")
        self.factory = MockFactory()
        self.pin_patch = patch.object(Device, "pin_factory", self.factory)
        self.pin_patch.start()
        self.addCleanup(self.pin_patch.stop)
        self.addCleanup(self.factory.close)

    def test_led_rejects_motor_gpio_aliases_including_disabled_motor(self) -> None:
        for enabled in (True, False):
            self.config.motors[0].enabled = enabled
            for pin in (26, "GPIO26", "BCM26", "BOARD37", "J8:37", "D14", "LED"):
                with self.subTest(pin=pin, enabled=enabled):
                    with self.assertRaisesRegex(ValueError, "motors\\[0\\].enable_pin"):
                        validate_led_pin(self.config, pin)
        validate_led_pin(self.config, 16)

    async def test_conflicting_led_never_creates_process(self) -> None:
        service = LEDService(MagicMock(), MagicMock(), self.manager)
        with patch("app.services.sensors.led_service.mp.Process") as process:
            with self.assertRaisesRegex(ValueError, "GPIO26"):
                await service.start_all()
            process.assert_not_called()

    async def test_ultrasonic_cannot_claim_motor_gpio(self) -> None:
        self.config.ultrasonic = UltrasonicConfig(trig_pin="D14", echo_pin="GPIO17")
        self.manager.load_data.return_value = self.config.model_dump(mode="json")
        service = DistanceService(
            MagicMock(), MagicMock(cancel_task=AsyncMock()), self.manager
        )
        with patch("app.services.sensors.distance_service.mp.Process") as process:
            with self.assertRaisesRegex(ValueError, "GPIO26"):
                await service.start_all()
            process.assert_not_called()

    async def test_process_cleanup_is_repeatable_and_cannot_restart(self) -> None:
        task_manager = MagicMock(cancel_task=AsyncMock())
        services = (
            LEDService(MagicMock(), task_manager, self.manager),
            DistanceService(MagicMock(), task_manager, self.manager),
        )
        for service in services:
            with self.subTest(service=type(service).__name__):
                process = MagicMock()
                process.is_alive.return_value = False
                service._process = process
                await service.cleanup()
                await service.cleanup()
                self.assertFalse(service.running)
                process.close.assert_called_once_with()
                with self.assertRaisesRegex(RuntimeError, "shut down"):
                    await service.start_all()

    async def test_changing_led_to_motor_pin_preserves_current_pin(self) -> None:
        self.config.led = (
            self.config.led.model_copy(update={"pin": 16}) if self.config.led else None
        )
        self.manager.load_data.return_value = self.config.model_dump(mode="json")
        service = LEDService(MagicMock(), MagicMock(), self.manager)
        with self.assertRaisesRegex(ValueError, "GPIO26"):
            await service.update_pin(26)
        assert service.led_config is not None
        self.assertEqual(service.led_config.pin, 16)

    async def test_concurrent_distance_starts_close_the_previous_process(self) -> None:
        service = DistanceService(
            MagicMock(emit=AsyncMock()), AsyncTaskManager(), self.manager
        )
        processes: list[MagicMock] = []

        def make_process(**kwargs: object) -> MagicMock:
            process = MagicMock()
            process.is_alive.return_value = True
            process.join.side_effect = lambda timeout: setattr(
                process.is_alive, "return_value", False
            )
            processes.append(process)
            return process

        with patch(
            "app.services.sensors.distance_service.mp.Process", side_effect=make_process
        ):
            try:
                await asyncio.gather(service.start_all(), service.start_all())
                self.assertEqual(len(processes), 2)
                processes[0].close.assert_called_once()
                processes[1].close.assert_not_called()
            finally:
                await service.cleanup()

    async def test_distance_config_callback_returns_to_the_watcher_loop(self) -> None:
        service = DistanceService(
            MagicMock(emit=AsyncMock()), AsyncTaskManager(), self.manager
        )
        process = MagicMock()
        process.is_alive.return_value = True
        process.join.side_effect = lambda timeout: setattr(
            process.is_alive, "return_value", False
        )
        with patch(
            "app.services.sensors.distance_service.mp.Process", return_value=process
        ):
            try:
                await service.start_all()
                candidate = self.config.model_copy(update={"ultrasonic": None})
                await asyncio.to_thread(
                    lambda: asyncio.run(
                        service.update_config(candidate.model_dump(mode="json"))
                    )
                )
                self.assertIsNone(service.robot_config.ultrasonic)
                self.assertFalse(service.running)
            finally:
                await service.cleanup()
