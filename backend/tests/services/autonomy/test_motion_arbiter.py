import math
import unittest
from dataclasses import replace

from app.services.autonomy import (
    IntentRejectionReason,
    MotionArbiter,
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


class MotionArbiterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.limits = MotionLimits(
            max_forward_speed_mps=1.0,
            max_reverse_speed_mps=0.5,
            max_abs_steering_angle_rad=0.6,
        )
        self.arbiter = MotionArbiter(self.limits, self.clock)

    def intent(
        self,
        *,
        command_id: str = "manual-1",
        source: MotionSource = MotionSource.MANUAL,
        sequence: int = 1,
        mode_generation: int = 1,
        speed: float = 0.4,
        steering: float = 0.1,
        created_ns: int | None = None,
        expires_ns: int | None = None,
        priority: int = 0,
    ) -> MotionIntent:
        created = self.clock.now_ns if created_ns is None else created_ns
        expires = created + 500_000_000 if expires_ns is None else expires_ns
        return MotionIntent(
            command_id=command_id,
            source=source,
            sequence=sequence,
            mode_generation=mode_generation,
            linear_speed_mps=speed,
            steering_angle_rad=steering,
            created_monotonic_ns=created,
            expires_monotonic_ns=expires,
            priority=priority,
        )

    def constraint(
        self,
        *,
        constraint_id: str = "front-zone",
        severity: SafetySeverity = SafetySeverity.LIMIT,
        reason: str = "obstacle ahead",
        forward_limit: float | None = 0.2,
        reverse_limit: float | None = None,
        created_ns: int | None = None,
        expires_ns: int | None = None,
    ) -> SafetyConstraint:
        return SafetyConstraint(
            constraint_id=constraint_id,
            source="test-safety",
            severity=severity,
            created_monotonic_ns=(
                self.clock.now_ns if created_ns is None else created_ns
            ),
            expires_monotonic_ns=expires_ns,
            max_forward_speed_mps=forward_limit,
            max_reverse_speed_mps=reverse_limit,
            reason=reason,
        )

    def submit_manual(self, intent: MotionIntent | None = None):
        return self.arbiter.submit(
            intent or self.intent(),
            mode=RobotMode.MANUAL,
            mode_generation=1,
        )

    def resolve_manual(self, constraints=()):
        return self.arbiter.resolve(
            mode=RobotMode.MANUAL,
            mode_generation=1,
            constraints=constraints,
        )


class TestMotionIntentValidation(MotionArbiterTestCase):
    def test_rejects_empty_command_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "command_id"):
            self.intent(command_id=" ")

    def test_rejects_invalid_sequence_and_generation(self) -> None:
        with self.assertRaisesRegex(ValueError, "sequence"):
            self.intent(sequence=-1)
        with self.assertRaisesRegex(ValueError, "mode_generation"):
            self.intent(mode_generation=-1)

    def test_rejects_invalid_validity_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "after creation"):
            self.intent(expires_ns=self.clock.now_ns)

    def test_rejects_non_finite_motion(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be finite"):
            self.intent(speed=math.inf)
        with self.assertRaisesRegex(ValueError, "must be finite"):
            self.intent(steering=math.nan)

    def test_rejects_limit_constraint_without_a_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "must define a speed limit"):
            self.constraint(forward_limit=None, reverse_limit=None)


class TestIntentSubmission(MotionArbiterTestCase):
    def test_accepts_source_matching_current_mode(self) -> None:
        cases = [
            (RobotMode.MANUAL, MotionSource.MANUAL),
            (RobotMode.AUTONOMOUS, MotionSource.AUTONOMY),
            (RobotMode.CALIBRATION, MotionSource.CALIBRATION),
        ]
        for index, (mode, source) in enumerate(cases):
            with self.subTest(mode=mode):
                intent = self.intent(
                    command_id=f"command-{index}", source=source, sequence=index + 1
                )
                result = self.arbiter.submit(intent, mode=mode, mode_generation=1)
                self.assertTrue(result.accepted)
                self.assertIsNone(result.rejection_reason)

    def test_rejects_source_not_allowed_in_current_mode(self) -> None:
        result = self.arbiter.submit(
            self.intent(source=MotionSource.AUTONOMY),
            mode=RobotMode.MANUAL,
            mode_generation=1,
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.rejection_reason, IntentRejectionReason.WRONG_MODE)

    def test_rejects_idle_and_safety_as_motion_intent_sources(self) -> None:
        for source in [MotionSource.IDLE, MotionSource.SAFETY]:
            with self.subTest(source=source):
                result = self.arbiter.submit(
                    self.intent(source=source),
                    mode=RobotMode.MANUAL,
                    mode_generation=1,
                )
                self.assertEqual(
                    result.rejection_reason,
                    IntentRejectionReason.SOURCE_NOT_COMMANDABLE,
                )

    def test_rejects_command_from_previous_mode_generation(self) -> None:
        result = self.arbiter.submit(
            self.intent(mode_generation=1),
            mode=RobotMode.MANUAL,
            mode_generation=2,
        )

        self.assertEqual(
            result.rejection_reason,
            IntentRejectionReason.WRONG_MODE_GENERATION,
        )

    def test_rejects_future_command(self) -> None:
        future = self.clock.now_ns + 1
        result = self.submit_manual(
            self.intent(created_ns=future, expires_ns=future + 100)
        )

        self.assertEqual(
            result.rejection_reason,
            IntentRejectionReason.CREATED_IN_FUTURE,
        )

    def test_rejects_already_expired_command(self) -> None:
        result = self.submit_manual(
            self.intent(
                created_ns=self.clock.now_ns - 100,
                expires_ns=self.clock.now_ns,
            )
        )

        self.assertEqual(result.rejection_reason, IntentRejectionReason.EXPIRED)

    def test_rejects_replayed_or_out_of_order_sequence(self) -> None:
        self.assertTrue(self.submit_manual(self.intent(sequence=5)).accepted)

        for sequence in [5, 4]:
            with self.subTest(sequence=sequence):
                result = self.submit_manual(
                    self.intent(command_id=f"manual-{sequence}", sequence=sequence)
                )
                self.assertEqual(
                    result.rejection_reason,
                    IntentRejectionReason.STALE_SEQUENCE,
                )

    def test_sequence_can_restart_after_mode_generation_changes(self) -> None:
        self.assertTrue(self.submit_manual(self.intent(sequence=5)).accepted)

        next_generation = self.arbiter.submit(
            self.intent(
                command_id="next-generation",
                sequence=0,
                mode_generation=2,
            ),
            mode=RobotMode.MANUAL,
            mode_generation=2,
        )

        self.assertTrue(next_generation.accepted)

    def test_expired_newer_command_does_not_restore_older_motion(self) -> None:
        self.assertTrue(self.submit_manual(self.intent(sequence=1)).accepted)
        expired = self.intent(
            command_id="manual-2",
            sequence=2,
            created_ns=self.clock.now_ns - 100,
            expires_ns=self.clock.now_ns,
        )

        result = self.submit_manual(expired)

        self.assertEqual(result.rejection_reason, IntentRejectionReason.EXPIRED)
        self.assertTrue(self.resolve_manual().command.is_stop)


class TestMotionResolution(MotionArbiterTestCase):
    def test_no_intent_resolves_to_explicit_idle_stop(self) -> None:
        result = self.resolve_manual()

        self.assertTrue(result.command.is_stop)
        self.assertEqual(result.command.source, MotionSource.IDLE)
        self.assertEqual(result.command.reason, "no valid motion intent")
        self.assertIsNone(result.selected_intent)

    def test_resolves_current_manual_intent(self) -> None:
        intent = self.intent(speed=0.4, steering=0.2)
        self.assertTrue(self.submit_manual(intent).accepted)

        result = self.resolve_manual()

        self.assertEqual(result.selected_intent, intent)
        self.assertEqual(result.command.command_id, intent.command_id)
        self.assertEqual(result.command.source, MotionSource.MANUAL)
        self.assertEqual(result.command.linear_speed_mps, 0.4)
        self.assertEqual(result.command.steering_angle_rad, 0.2)

    def test_newer_intent_replaces_older_intent(self) -> None:
        self.submit_manual(self.intent(command_id="old", sequence=1, speed=0.2))
        self.submit_manual(self.intent(command_id="new", sequence=2, speed=0.6))

        result = self.resolve_manual()

        self.assertEqual(result.command.command_id, "new")
        self.assertEqual(result.command.linear_speed_mps, 0.6)

    def test_intent_expires_using_monotonic_clock(self) -> None:
        intent = self.intent(expires_ns=self.clock.now_ns + 10)
        self.submit_manual(intent)
        self.assertFalse(self.resolve_manual().command.is_stop)

        self.clock.advance(10)

        self.assertTrue(self.resolve_manual().command.is_stop)

    def test_revoke_removes_source_without_resetting_sequence_guard(self) -> None:
        self.submit_manual(self.intent(sequence=3))
        self.arbiter.revoke(MotionSource.MANUAL)

        self.assertTrue(self.resolve_manual().command.is_stop)
        replay = self.submit_manual(self.intent(command_id="replay", sequence=3))
        self.assertEqual(
            replay.rejection_reason,
            IntentRejectionReason.STALE_SEQUENCE,
        )

    def test_mode_generation_change_invalidates_retained_command(self) -> None:
        self.submit_manual(self.intent(mode_generation=1))

        result = self.arbiter.resolve(
            mode=RobotMode.MANUAL,
            mode_generation=2,
        )

        self.assertTrue(result.command.is_stop)
        self.assertIsNone(result.selected_intent)

    def test_non_driving_modes_always_resolve_to_stop(self) -> None:
        self.submit_manual(self.intent())
        for mode, source in [
            (RobotMode.DISARMED, MotionSource.IDLE),
            (RobotMode.ESTOP, MotionSource.SAFETY),
            (RobotMode.FAULT, MotionSource.SAFETY),
        ]:
            with self.subTest(mode=mode):
                result = self.arbiter.resolve(mode=mode, mode_generation=1)
                self.assertTrue(result.command.is_stop)
                self.assertEqual(result.command.source, source)

    def test_physical_limits_clamp_forward_reverse_and_steering(self) -> None:
        cases = [
            (2.0, 1.2, 1.0, 0.6),
            (-2.0, -1.2, -0.5, -0.6),
        ]
        for index, (speed, steering, expected_speed, expected_steering) in enumerate(
            cases, start=1
        ):
            with self.subTest(speed=speed):
                arbiter = MotionArbiter(self.limits, self.clock)
                intent = self.intent(
                    command_id=f"limit-{index}",
                    sequence=index,
                    speed=speed,
                    steering=steering,
                )
                arbiter.submit(intent, mode=RobotMode.MANUAL, mode_generation=1)
                result = arbiter.resolve(mode=RobotMode.MANUAL, mode_generation=1)
                self.assertEqual(result.command.linear_speed_mps, expected_speed)
                self.assertEqual(result.command.steering_angle_rad, expected_steering)


class TestSafetyConstraints(MotionArbiterTestCase):
    def test_forward_limit_reduces_forward_motion_only(self) -> None:
        limit = self.constraint(forward_limit=0.2)
        self.submit_manual(self.intent(speed=0.7))

        forward = self.resolve_manual([limit])

        self.assertEqual(forward.command.linear_speed_mps, 0.2)
        self.assertEqual(forward.limiting_constraint_ids, ("front-zone",))

        reverse_arbiter = MotionArbiter(self.limits, self.clock)
        reverse = self.intent(command_id="reverse", speed=-0.4)
        reverse_arbiter.submit(reverse, mode=RobotMode.MANUAL, mode_generation=1)
        reverse_result = reverse_arbiter.resolve(
            mode=RobotMode.MANUAL,
            mode_generation=1,
            constraints=[limit],
        )
        self.assertEqual(reverse_result.command.linear_speed_mps, -0.4)
        self.assertEqual(reverse_result.limiting_constraint_ids, ())

    def test_reverse_limit_uses_positive_magnitude(self) -> None:
        limit = self.constraint(
            constraint_id="rear-zone",
            forward_limit=None,
            reverse_limit=0.1,
        )
        self.submit_manual(self.intent(speed=-0.4))

        result = self.resolve_manual([limit])

        self.assertEqual(result.command.linear_speed_mps, -0.1)
        self.assertEqual(result.limiting_constraint_ids, ("rear-zone",))

    def test_limit_never_accelerates_a_slower_command(self) -> None:
        limit = self.constraint(forward_limit=0.6)
        self.submit_manual(self.intent(speed=0.2))

        result = self.resolve_manual([limit])

        self.assertEqual(result.command.linear_speed_mps, 0.2)
        self.assertEqual(result.limiting_constraint_ids, ())

    def test_stop_constraint_overrides_selected_motion(self) -> None:
        stop = self.constraint(
            severity=SafetySeverity.STOP,
            forward_limit=None,
            reason="sensor data is stale",
        )
        intent = self.intent()
        self.submit_manual(intent)

        result = self.resolve_manual([stop])

        self.assertTrue(result.command.is_stop)
        self.assertEqual(result.command.source, MotionSource.SAFETY)
        self.assertEqual(result.command.reason, "sensor data is stale")
        self.assertEqual(result.selected_intent, intent)
        self.assertEqual(result.limiting_constraint_ids, ("front-zone",))

    def test_estop_constraint_overrides_all_motion(self) -> None:
        estop = self.constraint(
            constraint_id="operator-estop",
            severity=SafetySeverity.ESTOP,
            forward_limit=None,
            reason="operator emergency stop",
        )
        self.submit_manual(self.intent())

        result = self.resolve_manual([estop])

        self.assertTrue(result.command.is_stop)
        self.assertEqual(result.command.source, MotionSource.SAFETY)
        self.assertEqual(result.limiting_constraint_ids, ("operator-estop",))

    def test_expired_and_future_constraints_are_inactive(self) -> None:
        expired = self.constraint(
            constraint_id="expired",
            forward_limit=0.1,
            created_ns=self.clock.now_ns - 10,
            expires_ns=self.clock.now_ns,
        )
        future = self.constraint(
            constraint_id="future",
            forward_limit=0.1,
            created_ns=self.clock.now_ns + 10,
            expires_ns=self.clock.now_ns + 20,
        )
        self.submit_manual(self.intent(speed=0.5))

        result = self.resolve_manual([expired, future])

        self.assertEqual(result.command.linear_speed_mps, 0.5)
        self.assertEqual(result.active_constraints, ())

    def test_multiple_limits_apply_most_restrictive_value_and_preserve_reasons(
        self,
    ) -> None:
        first = self.constraint(
            constraint_id="battery",
            reason="low battery",
            forward_limit=0.4,
        )
        second = replace(
            first,
            constraint_id="front-zone",
            reason="obstacle ahead",
            max_forward_speed_mps=0.2,
        )
        self.submit_manual(self.intent(speed=0.8))

        result = self.resolve_manual([first, second])

        self.assertEqual(result.command.linear_speed_mps, 0.2)
        self.assertEqual(result.limiting_constraint_ids, ("battery", "front-zone"))
        self.assertEqual(result.command.reason, "low battery; obstacle ahead")


if __name__ == "__main__":
    unittest.main()
