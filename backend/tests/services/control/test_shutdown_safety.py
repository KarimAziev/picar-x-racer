import asyncio
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event, RLock
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from app.adapters.picarx_adapter import PicarxAdapter
from app.exceptions.robot import ServoNotFoundError
from app.services.control.car_service import CarService


class TestAdapterShutdownSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = PicarxAdapter.__new__(PicarxAdapter)
        self.adapter._hardware_lock = RLock()
        self.adapter._shutdown_requested = Event()
        self.adapter._pwm_drivers = {}
        self.adapter._pwm_driver_configs = {}
        self.adapter._motor_addresses = []
        self.adapter.steering_servo = None
        self.adapter.cam_pan_servo = None
        self.adapter.cam_tilt_servo = None
        self.controller = MagicMock()
        self.adapter.motor_controller = self.controller
        self.motors = [MagicMock(), MagicMock()]
        self.adapter.motors = [*self.motors]

    def test_missing_servo_does_not_prevent_shutdown(self) -> None:
        with self.assertRaises(ServoNotFoundError):
            self.adapter.set_dir_servo_angle(20)

        self.adapter.begin_shutdown()
        self.adapter.cleanup()
        self.adapter.cleanup()

        self.controller.stop_all.assert_called()
        self.controller.close.assert_called_once()
        self.assertIsNone(self.adapter.motor_controller)

    def test_stop_failure_still_closes_controller_and_servo(self) -> None:
        self.controller.stop_all.side_effect = OSError("motor bus offline")
        servo = MagicMock()
        self.adapter.cam_pan_servo = servo

        with self.assertRaisesRegex(RuntimeError, "Hardware cleanup failed"):
            self.adapter.cleanup()

        self.controller.close.assert_called_once()
        servo.close.assert_called_once()

    def test_controller_close_failure_attempts_each_motor(self) -> None:
        self.controller.close.side_effect = RuntimeError("controller close failed")
        self.motors[0].stop.side_effect = OSError("first motor stop failed")
        self.motors[0].close.side_effect = OSError("first motor close failed")

        with self.assertRaisesRegex(RuntimeError, "controller close failed"):
            self.adapter.cleanup()

        for motor in self.motors:
            motor.stop.assert_called_once()
            motor.close.assert_called_once()

    def test_partial_motor_initialization_stops_before_closing(self) -> None:
        self.adapter.motor_controller = None
        self.motors[0].stop.side_effect = OSError("first motor stop failed")

        with self.assertRaisesRegex(RuntimeError, "first motor stop failed"):
            self.adapter.cleanup()

        for motor in self.motors:
            self.assertEqual(
                [entry[0] for entry in motor.method_calls], ["stop", "close"]
            )

    def test_shutdown_latches_while_move_is_in_progress(self) -> None:
        entered = Event()
        release = Event()
        events: list[str] = []

        def moving(*_: Any) -> None:
            events.append("move")
            entered.set()
            if not release.wait(timeout=2):
                raise TimeoutError("test did not release moving command")

        self.controller.move.side_effect = moving
        self.controller.stop_all.side_effect = lambda: events.append("stop")
        with ThreadPoolExecutor(max_workers=3) as executor:
            moving_future = executor.submit(self.adapter.forward, 50)
            try:
                self.assertTrue(entered.wait(timeout=2))
                shutdown_future = executor.submit(self.adapter.begin_shutdown)
                self.assertTrue(self.adapter._shutdown_requested.wait(timeout=2))
                queued_future = executor.submit(self.adapter.move, 100, 1)
            finally:
                release.set()
            moving_future.result(timeout=2)
            shutdown_future.result(timeout=2)
            with self.assertRaisesRegex(RuntimeError, "shutting down"):
                queued_future.result(timeout=2)

        self.assertEqual(events, ["move", "stop"])
        with self.assertRaisesRegex(RuntimeError, "shutting down"):
            self.adapter.init_hardware()
        with self.assertRaisesRegex(RuntimeError, "shutting down"):
            with self.adapter.hardware_session():
                self.fail("shutdown must reject hardware configuration")
        with self.assertRaisesRegex(RuntimeError, "shutting down"):
            self.adapter.set_cam_pan_angle(30)


class TestCarShutdownSafety(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.car = CarService.__new__(CarService)
        self.car._shutting_down = False
        self.car._cleanup_lock = asyncio.Lock()
        self.car._cleanup_complete = False
        self.car._cleanup_error = None
        self.car._avoid_task = None
        self.car.avoid_obstacles_mode = True
        self.hardware = MagicMock()
        self.car.px = self.hardware
        self.distance = MagicMock(stop_all=AsyncMock())
        self.car.distance_service = self.distance
        self.motion = MagicMock(stop=AsyncMock())
        self.car.motion_control_service = self.motion

    async def test_cleanup_latches_before_stopping_background_services(self) -> None:
        events: list[str] = []

        def begin_shutdown() -> None:
            self.assertTrue(self.car._shutting_down)
            self.assertFalse(self.car.avoid_obstacles_mode)
            events.append("stop hardware")

        self.hardware.begin_shutdown.side_effect = begin_shutdown
        self.hardware.cleanup.side_effect = lambda: events.append("close hardware")
        self.motion.stop.side_effect = lambda: events.append("stop motion")
        self.distance.stop_all.side_effect = lambda: events.append("stop distance")

        await self.car.cleanup()
        await self.car.cleanup()

        self.assertEqual(
            events,
            ["stop hardware", "stop motion", "close hardware", "stop distance"],
        )
        with self.assertRaisesRegex(RuntimeError, "shutting down"):
            await self.car.move(1, 100)
        with self.assertRaisesRegex(RuntimeError, "shutting down"):
            await self.car.handle_avoid_obstacles()
        with self.assertRaisesRegex(RuntimeError, "shutting down"):
            await self.car.process_action("resetMCU", None, cast(Any, MagicMock()))

    async def test_cleanup_failure_is_reported_after_all_resources_are_attempted(
        self,
    ) -> None:
        self.hardware.begin_shutdown.side_effect = OSError("motor stop failed")
        self.motion.stop.side_effect = RuntimeError("watchdog failed")
        self.hardware.cleanup.side_effect = OSError("motor close failed")

        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, "motor stop failed"):
                await self.car.cleanup()

        self.motion.stop.assert_awaited_once()
        self.hardware.cleanup.assert_called_once()
        self.distance.stop_all.assert_awaited_once()

    async def test_request_cancellation_waits_for_hardware_cleanup(self) -> None:
        entered = asyncio.Event()
        release = asyncio.Event()

        async def stopping() -> None:
            entered.set()
            await release.wait()

        self.motion.stop.side_effect = stopping
        cleanup = asyncio.create_task(self.car.cleanup())
        await asyncio.wait_for(entered.wait(), timeout=2)
        cleanup.cancel()
        await asyncio.sleep(0)
        self.assertFalse(cleanup.done())
        release.set()

        with self.assertRaises(asyncio.CancelledError):
            await cleanup

        self.hardware.cleanup.assert_called_once()
        self.distance.stop_all.assert_awaited_once()
        self.assertTrue(self.car._cleanup_complete)

    async def test_canceled_background_service_does_not_skip_hardware_cleanup(
        self,
    ) -> None:
        self.motion.stop.side_effect = asyncio.CancelledError()

        with self.assertRaisesRegex(RuntimeError, "Robot cleanup failed"):
            await self.car.cleanup()

        self.hardware.cleanup.assert_called_once()
        self.distance.stop_all.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
