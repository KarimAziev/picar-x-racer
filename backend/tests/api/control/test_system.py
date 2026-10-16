import unittest
from unittest.mock import AsyncMock, MagicMock

from app.api.control.system import shutdown


class TestRobotShutdownEndpoint(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.order: list[str] = []
        self.robot = MagicMock(cleanup=self._cleanup("robot"))
        self.distance = MagicMock(cleanup=self._cleanup("distance"))
        self.led = MagicMock(cleanup=self._cleanup("led"))
        self.sensors = MagicMock(stop=self._cleanup("localization"))
        self.lidar = MagicMock(stop=self._cleanup("lidar"))
        self.mapping = MagicMock(stop=self._cleanup("mapping"))
        self.battery = MagicMock(cleanup_connection_manager=self._cleanup("battery"))
        self.auxiliary = MagicMock(
            cleanup_connection_manager=self._cleanup("auxiliary")
        )
        self.request = MagicMock()
        self.request.app.state.battery_service = self.battery
        self.request.app.state.auxiliary_sensor_service = self.auxiliary

    def _cleanup(self, name: str) -> AsyncMock:
        return AsyncMock(side_effect=lambda: self.order.append(name))

    async def test_motor_shutdown_precedes_other_service_cleanup(self) -> None:
        result = await shutdown(
            self.request,
            self.robot,
            self.distance,
            self.led,
            self.sensors,
            self.lidar,
            self.mapping,
        )

        self.assertEqual(result, {"success": True})
        self.assertEqual(self.order[0], "robot")
        self.assertEqual(len(self.order), 8)

    async def test_motor_cleanup_failure_is_returned_after_other_services_stop(
        self,
    ) -> None:
        self.robot.cleanup.side_effect = RuntimeError("motor stop failed")

        result = await shutdown(
            self.request,
            self.robot,
            self.distance,
            self.led,
            self.sensors,
            self.lidar,
            self.mapping,
        )

        self.assertEqual(result, {"success": False, "errors": ["motor stop failed"]})
        self.assertEqual(len(self.order), 7)


if __name__ == "__main__":
    unittest.main()
