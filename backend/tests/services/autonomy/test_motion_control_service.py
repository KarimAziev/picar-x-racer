import asyncio
import math
import unittest
from typing import List, Tuple, Union

from app.services.autonomy import (
    ActuationCalibration,
    HardwareController,
    LinearActuatorTranslator,
    ModeTransitionError,
    MotionArbiter,
    MotionControlService,
    MotionIntent,
    MotionLimits,
    MotionSource,
    RobotMode,
    SafetyConstraint,
    SafetySeverity,
)


class FakeClock:
    def __init__(self, now_ns: int = 1_000_000_000) -> None:
        self.now_ns = now_ns

    def monotonic_ns(self) -> int:
        return self.now_ns

    def advance(self, nanoseconds: int) -> None:
        self.now_ns += nanoseconds


class FakeDriveHardware:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, Union[int, float, None]]] = []
        self.fail_forward = False

    def forward(self, speed: int) -> None:
        self.calls.append(("forward", speed))
        if self.fail_forward:
            raise OSError("motor bus failed")

    def backward(self, speed: int) -> None:
        self.calls.append(("backward", speed))

    def stop(self) -> None:
        self.calls.append(("stop", None))

    def set_dir_servo_angle(self, value: float) -> None:
        self.calls.append(("steer", value))


class TestMotionControlService(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        limits = MotionLimits(
            max_forward_speed_mps=1.0,
            max_reverse_speed_mps=0.5,
            max_abs_steering_angle_rad=math.pi / 4,
        )
        self.arbiter = MotionArbiter(limits, self.clock)
        self.hardware = FakeDriveHardware()
        translator = LinearActuatorTranslator(
            ActuationCalibration(
                max_forward_speed_mps=1.0,
                max_reverse_speed_mps=0.5,
                max_abs_steering_angle_rad=math.pi / 4,
                max_forward_command=80,
                max_reverse_command=60,
            )
        )
        self.controller = HardwareController(self.hardware, translator)
        self.service = MotionControlService(
            self.arbiter,
            self.controller,
            control_period_seconds=0.001,
        )

    def intent(
        self,
        *,
        sequence: int = 1,
        generation: int | None = None,
        speed: float = 0.5,
        lifetime_ns: int = 100,
    ) -> MotionIntent:
        return MotionIntent(
            command_id=f"manual-{sequence}",
            source=MotionSource.MANUAL,
            sequence=sequence,
            mode_generation=(
                self.service.mode_generation if generation is None else generation
            ),
            linear_speed_mps=speed,
            steering_angle_rad=0.0,
            created_monotonic_ns=self.clock.now_ns,
            expires_monotonic_ns=self.clock.now_ns + lifetime_ns,
        )

    async def enter_manual_mode(self) -> None:
        await self.service.set_mode(RobotMode.MANUAL)
        self.hardware.calls.clear()

    async def test_starts_disarmed_and_applies_an_explicit_stop(self) -> None:
        result = await self.service.step()

        self.assertEqual(self.service.mode, RobotMode.DISARMED)
        self.assertTrue(result.command.is_stop)
        self.assertEqual(self.hardware.calls, [("steer", 0.0), ("stop", None)])

    async def test_mode_change_invalidates_old_generation_and_stops(self) -> None:
        await self.enter_manual_mode()
        self.assertTrue(self.service.submit(self.intent()).accepted)
        await self.service.step()
        self.hardware.calls.clear()

        result = await self.service.set_mode(RobotMode.AUTONOMOUS)

        self.assertEqual(self.service.mode_generation, 2)
        self.assertTrue(result.command.is_stop)
        self.assertEqual(self.hardware.calls, [("stop", None)])
        self.assertFalse(self.service.submit(self.intent(generation=1)).accepted)

    async def test_watchdog_step_stops_after_intent_expiry(self) -> None:
        await self.enter_manual_mode()
        self.assertTrue(self.service.submit(self.intent()).accepted)

        moving = await self.service.step()
        self.clock.advance(100)
        stopped = await self.service.step()

        self.assertFalse(moving.command.is_stop)
        self.assertTrue(stopped.command.is_stop)
        self.assertEqual(self.hardware.calls[-1], ("stop", None))

    async def test_active_safety_constraint_limits_applied_motion(self) -> None:
        await self.enter_manual_mode()
        self.service.submit(self.intent(speed=0.8))
        self.service.put_constraint(
            SafetyConstraint(
                constraint_id="slow-zone",
                source="test-lidar",
                severity=SafetySeverity.LIMIT,
                created_monotonic_ns=self.clock.now_ns,
                expires_monotonic_ns=self.clock.now_ns + 100,
                reason="obstacle nearby",
                max_forward_speed_mps=0.25,
            )
        )

        result = await self.service.step()

        self.assertEqual(result.command.linear_speed_mps, 0.25)
        self.assertEqual(result.limiting_constraint_ids, ("slow-zone",))
        self.assertEqual(self.hardware.calls[-1], ("forward", 20))

    async def test_hardware_failure_transitions_to_fault_and_invalidates_intents(
        self,
    ) -> None:
        await self.enter_manual_mode()
        self.service.submit(self.intent())
        self.hardware.fail_forward = True

        with self.assertRaisesRegex(OSError, "motor bus failed"):
            await self.service.step()

        self.assertEqual(self.service.mode, RobotMode.FAULT)
        self.assertEqual(self.service.mode_generation, 2)
        self.assertIsInstance(self.service.last_error, OSError)
        self.assertEqual(self.hardware.calls[-1], ("stop", None))

    async def test_emergency_stop_is_latched_until_explicitly_cleared(self) -> None:
        await self.enter_manual_mode()
        self.service.submit(self.intent())
        await self.service.step()

        stopped = await self.service.emergency_stop("operator button")

        self.assertTrue(stopped.command.is_stop)
        self.assertEqual(self.service.mode, RobotMode.ESTOP)
        self.assertEqual(self.service.estop_reason, "operator button")
        with self.assertRaisesRegex(ModeTransitionError, "latched"):
            await self.service.set_mode(RobotMode.MANUAL)

        disarmed = await self.service.clear_emergency_stop()

        self.assertEqual(self.service.mode, RobotMode.DISARMED)
        self.assertIsNone(self.service.estop_reason)
        self.assertTrue(disarmed.command.is_stop)

    async def test_clearing_estop_does_not_implicitly_rearm_motion(self) -> None:
        await self.enter_manual_mode()
        await self.service.emergency_stop("test")
        await self.service.clear_emergency_stop()

        result = self.service.submit(self.intent())

        self.assertFalse(result.accepted)

    async def test_fault_is_latched_and_can_only_clear_to_disarmed(self) -> None:
        await self.enter_manual_mode()
        self.service.submit(self.intent())
        self.hardware.fail_forward = True
        with self.assertRaises(OSError):
            await self.service.step()

        with self.assertRaisesRegex(ModeTransitionError, "fault is latched"):
            await self.service.set_mode(RobotMode.MANUAL)

        self.hardware.fail_forward = False
        result = await self.service.clear_fault()

        self.assertEqual(self.service.mode, RobotMode.DISARMED)
        self.assertIsNone(self.service.last_error)
        self.assertTrue(result.command.is_stop)

    async def test_periodic_loop_can_start_and_always_force_stops_on_shutdown(
        self,
    ) -> None:
        await self.enter_manual_mode()
        self.service.submit(self.intent(lifetime_ns=1_000_000))

        self.service.start()
        await asyncio.sleep(0.005)
        await self.service.stop()

        self.assertFalse(self.service.running)
        self.assertIn(("forward", 40), self.hardware.calls)
        self.assertEqual(self.hardware.calls[-1], ("stop", None))

    async def test_start_is_idempotent(self) -> None:
        self.service.start()
        first_task = self.service._task
        self.service.start()

        self.assertIs(self.service._task, first_task)
        await self.service.stop()


if __name__ == "__main__":
    unittest.main()
