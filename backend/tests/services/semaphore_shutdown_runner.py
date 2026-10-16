"""Exercise spawned sensor services under Uvicorn without opening GPIO devices."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import json
import multiprocessing as mp
from pathlib import Path
import signal
import sys
from typing import TYPE_CHECKING, AsyncIterator
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
import uvicorn

from app.core.async_emitter import AsyncEventEmitter
from app.managers.async_task_manager import AsyncTaskManager
from app.services.sensors.distance_service import DistanceService
from app.services.sensors.led_service import LEDService

if TYPE_CHECKING:
    from multiprocessing.connection import Connection
    from multiprocessing.sharedctypes import Synchronized
    from multiprocessing.synchronize import Event


def distance_worker(
    trig_pin: str | int,
    echo_pin: str | int,
    stop_event: Event,
    distance: Synchronized[float],
    interval: float,
    timeout: float,
) -> None:
    distance.value = 42.0
    stop_event.wait(15)


def led_worker(pin: str | int, stop_event: Event, interval: float) -> None:
    stop_event.wait(15)


def serve(ready: Connection, active: bool) -> None:
    config = json.loads(
        (Path(__file__).resolve().parents[3] / "config.json").read_text()
    )
    config["led"] = {"name": "Test LED", "pin": 16, "interval": 0.01}
    manager = MagicMock()
    manager.load_data.return_value = config

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        distance = DistanceService(
            AsyncEventEmitter(), AsyncTaskManager(), manager, interval=0.01
        )
        led = LEDService(AsyncEventEmitter(), AsyncTaskManager(), manager)
        # Dependency caches keep service instances alive after lifespan cleanup.
        app.state.sensor_services = (distance, led)

        async def report_ready() -> None:
            while not server.started:
                await asyncio.sleep(0.01)
            ready.send("ready")
            ready.close()

        readiness = asyncio.create_task(report_ready())
        try:
            if active:
                with (
                    patch(
                        "app.services.sensors.distance_service.distance_process",
                        distance_worker,
                    ),
                    patch("app.services.sensors.led_service.led_process", led_worker),
                ):
                    await distance.start_all()
                    await led.start_all()
            yield
        finally:
            readiness.cancel()
            with suppress(asyncio.CancelledError):
                await readiness
            await distance.cleanup()
            await led.cleanup()
            await distance.cleanup()
            await led.cleanup()
            print("sensor cleanup complete", flush=True)

    app = FastAPI(lifespan=lifespan)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    )
    server.run()


def main() -> None:
    context = mp.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=serve, args=(writer, sys.argv[1] == "active"))
    process.start()
    writer.close()
    try:
        if not reader.poll(10) or reader.recv() != "ready":
            raise RuntimeError("Sensor test server did not start")
        process.terminate()
        process.join(10)
        if process.is_alive():
            raise RuntimeError("Sensor test server did not shut down")
        if process.exitcode not in (0, -signal.SIGTERM):
            raise RuntimeError(f"Unexpected server exit code: {process.exitcode}")
    finally:
        reader.close()
        if process.is_alive():
            process.kill()
            process.join(5)
        process.close()


if __name__ == "__main__":
    main()
