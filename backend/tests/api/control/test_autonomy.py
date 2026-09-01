import unittest
from unittest.mock import Mock

from app.api.control.autonomy import get_simulation_status, reset_simulation
from app.services.autonomy import (
    AckermannSimulationConfig,
    AckermannSimulationPlant,
    CoherentSimulationService,
    CoherentSimulationSupervisor,
    RobotMode,
    TopicBus,
    build_simulation_world,
)
from fastapi import HTTPException


class FakeMotionControl:
    simulation_enabled = True

    def __init__(self) -> None:
        self.mode = RobotMode.MANUAL
        self.requested_modes: list[RobotMode] = []

    async def set_mode(self, mode: RobotMode) -> None:
        self.requested_modes.append(mode)
        self.mode = mode

    async def step(self) -> None:
        return None


class TestSimulationEndpoints(unittest.IsolatedAsyncioTestCase):
    def make_supervisor(self) -> CoherentSimulationSupervisor:
        bus = TopicBus()
        world = build_simulation_world("empty_room", width_m=6, height_m=4)
        return CoherentSimulationSupervisor(
            CoherentSimulationService(
                bus,
                AckermannSimulationPlant(
                    AckermannSimulationConfig(
                        wheelbase_m=0.25,
                        wheel_radius_m=0.03,
                        encoder_ticks_per_revolution=4096,
                    )
                ),
                world=world,
                initial_x_m=1,
                initial_y_m=-0.5,
                initial_yaw_rad=0.25,
            )
        )

    async def test_disabled_status_is_explicit(self) -> None:
        status = await get_simulation_status(
            CoherentSimulationSupervisor(),
            None,
        )

        self.assertFalse(status.enabled)
        self.assertFalse(status.running)
        self.assertFalse(status.physical_drive_isolated)

    async def test_reset_requires_enabled_isolated_runtime(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await reset_simulation(CoherentSimulationSupervisor(), None, None, None)

        self.assertEqual(context.exception.status_code, 409)

    async def test_reset_disarms_and_restarts_from_initial_pose(self) -> None:
        supervisor = self.make_supervisor()
        motion = FakeMotionControl()
        odometry = Mock()
        mapping = Mock()
        await supervisor.start()
        try:
            status = await reset_simulation(
                supervisor,
                motion,  # type: ignore[arg-type]
                odometry,
                mapping,
            )
        finally:
            await supervisor.stop()

        self.assertEqual(motion.requested_modes, [RobotMode.DISARMED])
        self.assertTrue(status.enabled)
        self.assertTrue(status.running)
        self.assertTrue(status.physical_drive_isolated)
        self.assertEqual(status.published_updates, 0)
        self.assertEqual(status.lidar_published_updates, 0)
        self.assertEqual(status.world.scenario, "empty_room")  # type: ignore[union-attr]
        self.assertEqual(status.odom_origin_in_world.x_m, 1)  # type: ignore[union-attr]
        odometry.reset.assert_called_once_with()
        mapping.reset_session.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
