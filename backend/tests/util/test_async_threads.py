import asyncio
import threading
import unittest

from app.util.async_threads import run_in_thread


class TestRunInThread(unittest.IsolatedAsyncioTestCase):
    async def test_returns_result_and_propagates_worker_failure(self):
        self.assertEqual(await run_in_thread(pow, 2, exp=3), 8)

        def fail():
            raise OSError("I2C read failed")

        with self.assertRaisesRegex(OSError, "I2C read failed"):
            await run_in_thread(fail)

    async def test_repeated_cancellation_retains_resource_until_worker_finishes(self):
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        resource_lock = asyncio.Lock()

        def operation():
            started.set()
            release.wait(timeout=2)
            finished.set()
            raise OSError("Device disconnected during cancellation")

        async def use_resource():
            async with resource_lock:
                await run_in_thread(operation)

        task = asyncio.create_task(use_resource())
        self.assertTrue(await asyncio.to_thread(started.wait, 1))
        try:
            for _ in range(2):
                task.cancel()
                await asyncio.sleep(0)
                self.assertFalse(task.done())
                self.assertTrue(resource_lock.locked())
        finally:
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertTrue(finished.is_set())
        self.assertFalse(resource_lock.locked())


if __name__ == "__main__":
    unittest.main()
