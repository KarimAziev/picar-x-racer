import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import MagicMock
import weakref

from app.core.async_emitter import AsyncEventEmitter
from app.managers.async_task_manager import AsyncTaskManager
from app.services.sensors.distance_service import DistanceService
from app.services.sensors.led_service import LEDService


class TestSensorIPCCleanup(unittest.IsolatedAsyncioTestCase):
    def make_service(
        self, service_type: type[LEDService] | type[DistanceService]
    ) -> LEDService | DistanceService:
        manager = MagicMock()
        manager.load_data.return_value = json.loads(
            (Path(__file__).resolve().parents[3] / "config.json").read_text()
        )
        service = service_type(AsyncEventEmitter(), AsyncTaskManager(), manager)
        self.addAsyncCleanup(service.cleanup)
        return service

    async def test_cleanup_releases_ipc_while_service_remains_cached(self) -> None:
        for service_type in (LEDService, DistanceService):
            with self.subTest(service=service_type.__name__):
                service = self.make_service(service_type)
                assert service.stop_event is not None
                event = weakref.ref(service.stop_event)
                distance = None
                if isinstance(service, DistanceService):
                    assert service._distance is not None
                    distance = weakref.ref(service._distance)
                    service._distance.value = 42.25
                    self.assertEqual(service.distance, 42.25)

                await service.cleanup()
                await service.stop_all()
                await service.cleanup()

                self.assertIsNone(event())
                if distance is not None:
                    self.assertIsNone(distance())
                self.assertFalse(service.running)
                if isinstance(service, DistanceService):
                    self.assertEqual(service.distance, 42.25)
                    await service.distance_watcher()
                with self.assertRaisesRegex(RuntimeError, "shut down"):
                    await service.start_all()

    async def test_stop_preserves_ipc_for_restart(self) -> None:
        for service_type in (LEDService, DistanceService):
            with self.subTest(service=service_type.__name__):
                service = self.make_service(service_type)
                event = service.stop_event
                assert event is not None
                process = MagicMock()
                process.is_alive.return_value = False
                service._process = process

                await service.stop_all()

                self.assertIs(service.stop_event, event)
                self.assertFalse(event.is_set())
                process.close.assert_called_once_with()
                if isinstance(service, DistanceService):
                    self.assertIsNotNone(service._distance)

    async def test_live_worker_retains_ipc_until_cleanup_succeeds(self) -> None:
        for service_type in (LEDService, DistanceService):
            with self.subTest(service=service_type.__name__):
                service = self.make_service(service_type)
                assert service.stop_event is not None
                event = weakref.ref(service.stop_event)
                process = MagicMock()
                process.is_alive.return_value = True
                service._process = process
                try:
                    with self.assertRaisesRegex(RuntimeError, "process did not stop"):
                        await service.cleanup()
                    self.assertIsNotNone(event())
                    self.assertIs(service.stop_event, event())
                    process.terminate.assert_called_once_with()
                    process.close.assert_not_called()
                    if isinstance(service, DistanceService):
                        self.assertIsNotNone(service._distance)
                finally:
                    process.is_alive.return_value = False
                    await service.cleanup()
                self.assertIsNone(event())
                process.close.assert_called_once_with()

    async def test_cancelled_cleanup_waits_for_worker_and_releases_ipc(self) -> None:
        for service_type in (LEDService, DistanceService):
            with self.subTest(service=service_type.__name__):
                service = self.make_service(service_type)
                assert service.stop_event is not None
                event = weakref.ref(service.stop_event)
                joining = threading.Event()
                allow_exit = threading.Event()
                process = MagicMock()
                process.is_alive.return_value = True

                def join(timeout: float) -> None:
                    joining.set()
                    if not allow_exit.wait(5):
                        raise RuntimeError("Test worker was not released")
                    process.is_alive.return_value = False

                process.join.side_effect = join
                service._process = process
                cleanup = asyncio.create_task(service.cleanup())
                try:
                    self.assertTrue(await asyncio.to_thread(joining.wait, 2))
                    for _ in range(2):
                        cleanup.cancel()
                        await asyncio.sleep(0)
                    self.assertFalse(cleanup.done())
                    self.assertIsNotNone(event())
                    process.close.assert_not_called()
                finally:
                    allow_exit.set()
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(cleanup, 2)
                self.assertIsNone(event())
                process.close.assert_called_once_with()

    async def test_distance_cleanup_drains_watcher_before_releasing_ipc(self) -> None:
        service = self.make_service(DistanceService)
        assert isinstance(service, DistanceService)
        started = asyncio.Event()
        stopping = asyncio.Event()
        allow_exit = asyncio.Event()

        async def watcher() -> None:
            started.set()
            try:
                await asyncio.Future()
            finally:
                stopping.set()
                await allow_exit.wait()
                self.assertIsNotNone(service.stop_event)
                self.assertIsNotNone(service._distance)

        service._task_manager.start_task(watcher)
        await asyncio.wait_for(started.wait(), 2)
        cleanup = asyncio.create_task(service.cleanup())
        try:
            await asyncio.wait_for(stopping.wait(), 2)
            cleanup.cancel()
            await asyncio.sleep(0)
            self.assertFalse(cleanup.done())
            self.assertIsNotNone(service.stop_event)
        finally:
            allow_exit.set()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(cleanup, 2)
        self.assertIsNone(service.stop_event)
        self.assertIsNone(service._distance)


class TestSensorShutdownProcess(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "Requires POSIX signal handling")
    def test_uvicorn_sigterm_releases_semaphores_before_process_exit(self) -> None:
        for state in ("idle", "active"):
            with self.subTest(state=state):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "tests.services.semaphore_shutdown_runner",
                        state,
                    ],
                    cwd=Path(__file__).resolve().parents[2],
                    capture_output=True,
                    text=True,
                    timeout=35,
                    check=False,
                )
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertIn("sensor cleanup complete", output)
                self.assertNotIn("resource_tracker:", output)
