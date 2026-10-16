import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI

from app.control_server import lifespan
from app.api.robot_deps import LifespanAppDeps


class TestControlLifespanSafety(unittest.IsolatedAsyncioTestCase):
    async def test_motor_cleanup_precedes_telemetry_and_survives_errors(self) -> None:
        for failure in (RuntimeError("sensor failed"), asyncio.CancelledError()):
            with self.subTest(failure=type(failure).__name__):
                events: list[str] = []

                async def robot_cleanup() -> None:
                    events.append("motors")

                async def battery_cleanup() -> None:
                    events.append("battery")
                    raise failure

                async def auxiliary_cleanup() -> None:
                    events.append("auxiliary")

                robot = MagicMock(cleanup=AsyncMock(side_effect=robot_cleanup))
                distance = MagicMock(cleanup=AsyncMock(), start_all=AsyncMock())
                led = MagicMock(cleanup=AsyncMock())
                settings = MagicMock()
                settings.load_data.return_value = {}
                values = MagicMock(spec=dict)
                deps_by_name = {
                    "robot_service": robot,
                    "connection_service": MagicMock(),
                    "distance_service": distance,
                    "led_service": led,
                    "settings_service": settings,
                    "config_manager": MagicMock(),
                    "smbus_manager": MagicMock(),
                }
                values.get.side_effect = deps_by_name.get

                @asynccontextmanager
                async def dependencies(app: FastAPI) -> AsyncIterator[LifespanAppDeps]:
                    yield values

                battery = MagicMock(
                    cleanup_connection_manager=AsyncMock(side_effect=battery_cleanup)
                )
                auxiliary = MagicMock(
                    cleanup_connection_manager=AsyncMock(side_effect=auxiliary_cleanup)
                )
                with (
                    patch(
                        "app.util.solve_lifespan.solve_lifespan",
                        return_value=dependencies,
                    ),
                    patch("app.control_server.BatteryService", return_value=battery),
                    patch(
                        "app.control_server.AuxiliarySensorService",
                        return_value=auxiliary,
                    ),
                ):
                    if isinstance(failure, asyncio.CancelledError):
                        with self.assertRaises(asyncio.CancelledError):
                            async with lifespan(FastAPI()):
                                pass
                    else:
                        async with lifespan(FastAPI()):
                            pass
                self.assertEqual(events, ["motors", "battery", "auxiliary"])
                distance.cleanup.assert_awaited_once()
                led.cleanup.assert_awaited_once()

    async def test_startup_failure_still_stops_initialized_motors(self) -> None:
        robot = MagicMock(cleanup=AsyncMock())
        values = MagicMock(spec=dict)
        values.get.side_effect = {"robot_service": robot}.get

        @asynccontextmanager
        async def dependencies(app: FastAPI) -> AsyncIterator[LifespanAppDeps]:
            yield values

        with (
            patch("app.util.solve_lifespan.solve_lifespan", return_value=dependencies),
            patch(
                "app.control_server.BatteryService",
                side_effect=RuntimeError("startup failed"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "startup failed"):
                async with lifespan(FastAPI()):
                    self.fail("startup should not yield")
        robot.cleanup.assert_awaited_once()
