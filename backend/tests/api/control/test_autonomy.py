import unittest

from app.api.control.autonomy import get_simulation_status, reset_simulation
from app.services.autonomy import (
    AckermannSimulationConfig,
    AckermannSimulationPlant,
    CoherentSimulationService,
    CoherentSimulationSupervisor,
    RobotMode,
    TopicBus,
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
            await reset_simulation(CoherentSimulationSupervisor(), None)

        self.assertEqual(context.exception.status_code, 409)

    async def test_reset_disarms_and_restarts_from_initial_pose(self) -> None:
        supervisor = self.make_supervisor()
        motion = FakeMotionControl()
        await supervisor.start()
        try:
            status = await reset_simulation(supervisor, motion)  # type: ignore[arg-type]
        finally:
            await supervisor.stop()

        self.assertEqual(motion.requested_modes, [RobotMode.DISARMED])
        self.assertTrue(status.enabled)
        self.assertTrue(status.running)
        self.assertTrue(status.physical_drive_isolated)
        self.assertEqual(status.published_updates, 0)


if __name__ == "__main__":
    unittest.main()
