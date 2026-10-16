import asyncio
from contextlib import contextmanager
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Iterator
import unittest
from unittest.mock import MagicMock, patch

from app.adapters.picarx_adapter import PicarxAdapter
from app.core.event_emitter import EventEmitter
from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.motors import GPIODCMotorConfig
from app.services.control.settings_service import SettingsService
from app.services.sensors.led_service import LEDService


class TestLEDHardwareSynchronization(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.config = HardwareConfig.model_validate_json(
            (Path(__file__).resolve().parents[3] / "config.json").read_text()
        )
        self.manager = MagicMock()
        self.manager.load_data.return_value = self.config.model_dump(mode="json")
        self.manager.update.side_effect = lambda data, **kwargs: data
        self.adapter = PicarxAdapter.__new__(PicarxAdapter)
        self.adapter._hardware_lock = RLock()
        self.adapter._shutdown_requested = Event()
        self.adapter.config = self.config.model_copy(deep=True)
        self.adapter.motor_controller = MagicMock()
        self.adapter._motor_addresses = []
        self.led = LEDService(MagicMock(), MagicMock(), self.manager)
        self.settings = SettingsService(
            self.adapter, self.manager, led_service=self.led
        )

    async def test_pin_update_waits_for_activation_then_checks_active_hardware(
        self,
    ) -> None:
        entered = Event()
        release = Event()
        attempted = Event()
        candidate = self.config.model_copy(deep=True)
        candidate.motors = [
            GPIODCMotorConfig(
                name="Drive",
                forward_pin="GPIO20",
                backward_pin="GPIO21",
                enable_pin="GPIO25",
            )
        ]

        def activate() -> None:
            with self.adapter.hardware_session():
                self.adapter.config = candidate
                entered.set()
                release.wait(timeout=2)

        def attempting_session():
            attempted.set()
            return self.adapter.hardware_session()

        worker = Thread(target=activate, daemon=True)
        worker.start()
        self.assertTrue(await asyncio.to_thread(entered.wait, 2))
        try:
            with patch.object(
                self.led, "_hardware_session", side_effect=attempting_session
            ):
                update = asyncio.create_task(self.led.update_pin("GPIO20"))
                self.assertTrue(await asyncio.to_thread(attempted.wait, 2))
                self.assertFalse(update.done())
                assert self.led.led_config is not None
                self.assertEqual(self.led.led_config.pin, 26)
                release.set()
                with self.assertRaisesRegex(ValueError, "GPIO20"):
                    await update
        finally:
            release.set()
            await asyncio.to_thread(worker.join, 2)
        self.assertEqual(self.led.led_config.pin, 26)

    async def test_settings_callback_can_restart_led_without_holding_adapter_lock(
        self,
    ) -> None:
        emitter = EventEmitter()
        emitter.on("update", self.led.update_config)
        self.manager.UPDATE_EVENT = "update"
        self.manager.emit.side_effect = emitter.emit
        old_process = MagicMock()
        old_process.is_alive.return_value = True
        old_process.join.side_effect = lambda _: old_process.is_alive.configure_mock(
            return_value=False
        )
        self.led._process = old_process

        @contextmanager
        def bounded_session() -> Iterator[None]:
            if not self.adapter._hardware_lock.acquire(timeout=1):
                raise TimeoutError("actuator lock is held during sensor notification")
            try:
                yield
            finally:
                self.adapter._hardware_lock.release()

        with patch.object(
            self.adapter, "hardware_session", side_effect=bounded_session
        ), patch("app.services.sensors.led_service.mp.Process") as process:
            await asyncio.to_thread(self.settings.save_settings, self.config)

        process.assert_called_once()
        process.return_value.start.assert_called_once()
        self.manager.update.assert_called_once_with(
            self.settings._model_json_dump(self.config), emit_event=False
        )

    async def test_motor_stop_is_available_during_settings_notification(self) -> None:
        stopped = Event()

        def stop_motor() -> None:
            self.adapter.stop()
            stopped.set()

        def notify(*_: object) -> None:
            worker = Thread(target=stop_motor, daemon=True)
            worker.start()
            if not stopped.wait(timeout=1):
                raise TimeoutError("sensor notification blocked motor stop")

        self.manager.emit.side_effect = notify

        await asyncio.to_thread(self.settings.save_settings, self.config)

        self.assertTrue(stopped.is_set())

    async def test_led_alias_is_normalized_before_child_process_starts(self) -> None:
        assert self.led.led_config is not None
        self.led.led_config.pin = "D14"
        with patch("app.services.sensors.led_service.mp.Process") as process:
            await self.led.start_all()

        self.assertEqual(process.call_args.kwargs["args"][0], 26)


if __name__ == "__main__":
    unittest.main()
