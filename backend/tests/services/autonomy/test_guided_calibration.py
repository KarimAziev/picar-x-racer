import asyncio
import json
import math
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from app.schemas.autonomy import EncoderReading, EncoderState, LaserScan, MessageHeader
from app.schemas.autonomy.calibration import (
    CalibrationApply,
    CalibrationFinish,
    CalibrationHeartbeat,
    CalibrationStart,
)
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.services.autonomy.calibration import (
    CalibrationError,
    GuidedCalibrationService,
    Observation,
    Session,
    config_fingerprint,
    fit_speed,
)
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.motion_control_service import MotionControlService
from app.services.autonomy.messages import RobotMode
from app.services.autonomy.topics import ENCODER_STATE, LIDAR_SCAN
from app.services.control.settings_service import SettingsService


class FakeHardware:
    def __init__(self):
        self.calibration_interrupted = False
        self.owner = None
        self.power = 0
        self.commands: list[tuple[int, float | None]] = []
        self.fail = False

    def acquire_calibration(self, owner: str):
        if self.owner:
            raise RuntimeError("Already owned")
        self.owner = owner
        self.power = 0
        self.calibration_interrupted = False

    def calibration_command(
        self, owner: str, power: int, steering_degrees: float | None = None
    ):
        if owner != self.owner or self.calibration_interrupted or self.fail:
            raise RuntimeError("Hardware unavailable")
        self.power = power
        self.commands.append((power, steering_degrees))

    def release_calibration(self, owner: str):
        if self.owner == owner:
            self.power = 0
            self.owner = None


def configuration() -> HardwareConfig:
    data = json.loads((Path(__file__).resolve().parents[4] / "config.json").read_text())
    data["localization_sensors"]["encoder"] = {
        "enabled": True,
        "sensors": [{"driver": "as5048a", "role": "rear_axle_average"}],
    }
    data["localization_sensors"]["lidar"].update(
        enabled=True, range_min_m=0.05, range_max_m=12
    )
    data["navigation"].update(body_length_m=0.4, body_width_m=0.2, rear_overhang_m=0.1)
    return HardwareConfig.model_validate(data)


def observation(
    t: float, ticks: int = 0, wall: float | None = None, gyro: float | None = None
) -> Observation:
    return Observation(
        t,
        (ticks,),
        round(t * 100),
        wall,
        t if wall is not None else None,
        gyro,
        t if gyro is not None else None,
        None,
    )


class TestGuidedCalibration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = 10.0
        self.config = configuration()
        self.settings = MagicMock(spec=SettingsService)
        self.settings.saved_settings = self.config
        self.hardware = FakeHardware()
        self.bus = TopicBus()
        self.service = GuidedCalibrationService(
            self.bus, self.hardware, self.settings, clock=lambda: self.now
        )
        self.publish()

    async def asyncTearDown(self):
        await self.service.stop()

    def publish(self, ticks: int = 0, distance: float = 3):
        header = MessageHeader(
            sequence=round(self.now * 100),
            timestamp_monotonic_ns=round(self.now * 1e9),
            frame_id="base_link",
        )
        self.bus.publish(
            ENCODER_STATE,
            EncoderState(
                header=header,
                rear_axle_average=EncoderReading(ticks=ticks, delta_ticks=0),
            ),
        )
        ranges = tuple(
            distance / max(abs(math.cos(math.radians(i))), 0.1)
            for i in range(-180, 180)
        )
        self.bus.publish(
            LIDAR_SCAN,
            LaserScan(
                header=header,
                angle_min_rad=-math.pi,
                angle_max_rad=math.pi - math.pi / 180,
                angle_increment_rad=math.pi / 180,
                range_min_m=0.05,
                range_max_m=50,
                ranges_m=ranges,
            ),
        )

    def session(self, kind="wheel_distance", **kwargs) -> Session:
        request = CalibrationStart.model_validate(
            {"kind": kind, "clear_path_confirmed": True, **kwargs}
        )
        return Session(
            "trial", request, self.config, config_fingerprint(self.config), 10, 10
        )

    async def test_emergency_stop_during_hardware_acquisition_aborts_start(self):
        motion = MagicMock(spec=MotionControlService)
        motion.mode = RobotMode.DISARMED
        motion.autonomy_owner = None
        motion.set_mode = AsyncMock()
        motion.stop = AsyncMock()
        self.service.motion = motion
        acquire = self.hardware.acquire_calibration

        def interrupted_acquire(owner: str):
            acquire(owner)
            motion.mode = RobotMode.ESTOP

        self.hardware.acquire_calibration = interrupted_acquire
        with self.assertRaisesRegex(CalibrationError, "during startup"):
            await self.service.start(
                CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
            )
        self.assertIsNone(self.hardware.owner)
        self.assertIsNone(self.service.session)
        self.assertEqual(motion.mode, RobotMode.ESTOP)

    async def test_legacy_obstacle_avoidance_blocks_calibration(self):
        self.service.autonomous_active = lambda: True
        with self.assertRaisesRegex(CalibrationError, "Avoid obstacles"):
            await self.service.start(
                CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
            )
        self.assertIsNone(self.hardware.owner)

    async def test_passive_measurement_does_not_move_steering_or_motors(self):
        result = await self.service.start(
            CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
        )
        assert result.session_id
        await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=1)
        )
        self.assertEqual(self.hardware.commands, [(0, None)])
        with self.assertRaisesRegex(CalibrationError, "motors stopped"):
            await self.service.heartbeat(
                result.session_id, CalibrationHeartbeat(sequence=2, drive=True)
            )
        self.assertEqual(self.hardware.power, 0)

    async def test_exclusive_session_and_explicit_ready_check(self):
        with self.assertRaisesRegex(CalibrationError, "Confirm"):
            await self.service.start(CalibrationStart(kind="wheel_distance"))
        await self.service.start(
            CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
        )
        with self.assertRaisesRegex(CalibrationError, "Another calibration"):
            await self.service.start(
                CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
            )

    async def test_powered_trial_without_motion_control_or_odometry(self):
        self.assertFalse(self.config.motion_control.enabled)
        self.assertFalse(self.config.ackermann_odometry.enabled)
        result = await self.service.start(
            CalibrationStart(kind="speed", clear_path_confirmed=True)
        )
        assert result.session_id
        await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=1, drive=True)
        )
        self.assertEqual(self.hardware.power, 20)
        await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=3, drive=False)
        )
        self.assertEqual(self.hardware.power, 0)
        with self.assertRaisesRegex(CalibrationError, "Out-of-order"):
            await self.service.heartbeat(
                result.session_id, CalibrationHeartbeat(sequence=2, drive=True)
            )
        with self.assertRaisesRegex(CalibrationError, "One movement"):
            await self.service.heartbeat(
                result.session_id, CalibrationHeartbeat(sequence=4, drive=True)
            )
        self.assertEqual(self.hardware.power, 0)

    async def test_late_heartbeat_cannot_revive_drive(self):
        result = await self.service.start(
            CalibrationStart(kind="speed", clear_path_confirmed=True)
        )
        assert result.session_id
        await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=1, drive=True)
        )
        self.now += 0.36
        self.publish()
        with self.assertRaisesRegex(CalibrationError, "expired"):
            await self.service.heartbeat(
                result.session_id, CalibrationHeartbeat(sequence=2, drive=True)
            )
        self.assertEqual(self.hardware.power, 0)
        self.assertIsNone(self.service.session)

    async def test_watchdog_stops_when_browser_disappears(self):
        result = await self.service.start(
            CalibrationStart(kind="speed", clear_path_confirmed=True)
        )
        assert result.session_id
        await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=1, drive=True)
        )
        self.now += 0.36
        await asyncio.sleep(0.08)
        self.assertEqual(self.hardware.power, 0)
        self.assertIsNone(self.service.session)
        self.assertFalse(self.service.trials[-1].accepted)

    async def test_stale_sensors_stop_before_next_command(self):
        result = await self.service.start(
            CalibrationStart(kind="speed", clear_path_confirmed=True)
        )
        assert result.session_id
        await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=1, drive=True)
        )
        self.now += 0.28
        with self.assertRaisesRegex(CalibrationError, "fresh wheel"):
            await self.service.heartbeat(
                result.session_id, CalibrationHeartbeat(sequence=2, drive=True)
            )
        self.assertEqual(self.hardware.power, 0)
        self.assertIsNone(self.service.session)

    async def test_boundary_and_hardware_error_stop_trial(self):
        for hardware_failure in (False, True):
            with self.subTest(hardware_failure=hardware_failure):
                self.publish()
                self.hardware.fail = False
                result = await self.service.start(
                    CalibrationStart(kind="speed", clear_path_confirmed=True)
                )
                assert result.session_id
                await self.service.heartbeat(
                    result.session_id, CalibrationHeartbeat(sequence=1, drive=True)
                )
                if hardware_failure:
                    self.hardware.fail = True
                else:
                    self.publish(distance=0.5)
                with self.assertRaises(CalibrationError):
                    await self.service.heartbeat(
                        result.session_id, CalibrationHeartbeat(sequence=2, drive=True)
                    )
                self.assertEqual(self.hardware.power, 0)
                self.assertIsNone(self.service.session)

    async def test_external_stop_is_not_rearmed(self):
        result = await self.service.start(
            CalibrationStart(kind="speed", clear_path_confirmed=True)
        )
        assert result.session_id
        await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=1, drive=True)
        )
        self.hardware.calibration_interrupted = True
        result = await self.service.heartbeat(
            result.session_id, CalibrationHeartbeat(sequence=2, drive=True)
        )
        self.assertFalse(result.active)
        self.assertEqual(self.hardware.power, 0)

    async def test_changed_configuration_invalidates_running_measurement(self):
        await self.service.start(
            CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
        )
        self.settings.saved_settings = self.config.model_copy(deep=True)
        self.settings.saved_settings.ackermann_odometry.gear_ratio = 2
        await asyncio.sleep(0.08)
        self.assertIsNone(self.service.session)
        self.assertIn("settings changed", self.service.trials[-1].reason)

    async def test_shutdown_releases_hardware(self):
        await self.service.start(
            CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
        )
        await self.service.stop()
        self.assertIsNone(self.hardware.owner)
        self.assertIsNone(self.service.session)

    def test_power_limit_and_mock_sensor_blockers(self):
        self.config.coherent_simulation.enabled = True
        self.assertIn(
            "Turn off Coherent",
            self.service.blockers(
                CalibrationStart(kind="speed"),
                self.config,
                self.service.observation(self.config),
            )[0],
        )

    async def test_initial_power_limit_is_enforced(self):
        with self.assertRaisesRegex(CalibrationError, "20%"):
            await self.service.start(
                CalibrationStart(
                    kind="speed", power_percent=80, clear_path_confirmed=True
                )
            )

    async def test_wall_fit_rejects_stale_or_tilted_plane(self):
        self.assertAlmostEqual(self.service.observation(self.config).wall_m or 0, 3)
        self.config.localization_sensors.lidar.transform.yaw_rad = 0.3
        self.assertIsNone(self.service.observation(self.config).wall_m)
        self.config.localization_sensors.lidar.transform.yaw_rad = 0
        self.now += 0.4
        self.assertIsNone(self.service.observation(self.config).wall_m)

    def test_distance_measurement_and_repeatability(self):
        session = self.session()
        session.observations = [observation(10, 0), observation(11, 1000)]
        trial = self.service.analyze(session, CalibrationFinish(measured_distance_m=1))
        self.assertAlmostEqual(trial.distance_per_tick_m or 0, 0.001)
        self.service.trials = [trial, trial.model_copy(update={"id": "second"})]
        update = self.service.proposed_update(
            CalibrationApply(trial_ids=["trial", "second"])
        )
        self.assertAlmostEqual(
            update["ackermann_odometry"]["wheel_radius_m"],
            0.001 * 16384 / (2 * math.pi),
        )
        self.settings.merge_if_current.assert_not_called()
        self.service.trials[1].distance_per_tick_m = 0.002
        with self.assertRaisesRegex(CalibrationError, "5%"):
            self.service.proposed_update(
                CalibrationApply(trial_ids=["trial", "second"])
            )

    def test_rejects_reversed_and_missing_wheel_readings(self):
        session = self.session()
        session.observations = [observation(10, 0), observation(11, -1000)]
        with self.assertRaisesRegex(CalibrationError, "forward"):
            self.service.analyze(session, CalibrationFinish(measured_distance_m=1))
        session.observations = [
            observation(10, 0),
            Observation(11, None, None, None, None, None, None, None),
        ]
        with self.assertRaisesRegex(CalibrationError, "readings stopped"):
            self.service.analyze(session, CalibrationFinish(measured_distance_m=1))

    def test_stationary_bias_uses_distinct_sensor_samples(self):
        session = self.session("imu_bias")
        session.observations = [
            observation(10 + i * 0.05, gyro=0.012) for i in range(81)
        ]
        trial = self.service.analyze(session, CalibrationFinish())
        self.assertAlmostEqual(trial.gyro_bias_radps or 0, 0.012)
        session.observations = [observation(10, gyro=0.012)] * 100
        with self.assertRaisesRegex(CalibrationError, "fresh IMU"):
            self.service.analyze(session, CalibrationFinish())

    def speed_session(self, reverse=False) -> Session:
        session = self.session("speed", direction="reverse" if reverse else "forward")
        session.drive_started, session.released = 10, 13
        sign = 1 if reverse else -1
        session.observations = [
            observation(
                10 + i * 0.1,
                int(min(i, 30) * 10 * -sign),
                4 + sign * 0.2 * min(i * 0.1, 3),
            )
            for i in range(41)
        ]
        self.now = 14
        return session

    def test_speed_uses_distance_and_sensor_time_in_both_directions(self):
        for reverse in (False, True):
            trial = self.service.analyze(
                self.speed_session(reverse), CalibrationFinish()
            )
            self.assertAlmostEqual(trial.mean_speed_mps or 0, 0.2)
            self.assertAlmostEqual(trial.minimum_speed_mps or 0, 0.2)
            self.assertAlmostEqual(trial.maximum_speed_mps or 0, 0.2)

    def test_wrong_motor_direction_does_not_unlock_higher_power(self):
        session = self.speed_session()
        session.request.direction = "reverse"
        with self.assertRaisesRegex(CalibrationError, "opposite"):
            self.service.analyze(session, CalibrationFinish())

    def test_speed_curve_requires_repeat_trials_and_increasing_levels(self):
        trial = self.service.analyze(self.speed_session(), CalibrationFinish())
        self.service.trials = [
            trial.model_copy(
                update={
                    "id": f"{direction}-{power}-{n}",
                    "direction": direction,
                    "power_percent": power,
                    "mean_speed_mps": power * 0.01,
                }
            )
            for direction in ("forward", "reverse")
            for power in (20, 30)
            for n in (1, 2)
        ]
        update = self.service.proposed_update(
            CalibrationApply(trial_ids=[t.id for t in self.service.trials])
        )
        self.assertEqual(update["motion_control"]["max_forward_speed_mps"], 0.3)
        self.assertEqual(
            update["motion_control"]["reverse_speed_curve"][0]["power_percent"], 20
        )
        with self.assertRaisesRegex(CalibrationError, "two trials"):
            self.service.proposed_update(
                CalibrationApply(trial_ids=[t.id for t in self.service.trials[:-1]])
            )

    def test_review_rejects_trials_from_different_settings(self):
        trial = self.service.analyze(self.speed_session(), CalibrationFinish())
        self.service.trials = [trial]
        self.config.ackermann_odometry.gear_ratio = 2
        with self.assertRaisesRegex(CalibrationError, "settings changed"):
            self.service.proposed_update(CalibrationApply(trial_ids=[trial.id]))

    async def test_apply_saves_reviewed_measurement_without_enabling_features(self):
        session = self.session("imu_bias")
        trial = self.service._trial(session, True, "Measured", gyro_bias_radps=0.012)
        self.service.trials = [trial, trial.model_copy(update={"id": "repeat"})]
        saved = PartialHardwareConfig.model_validate(
            {"pose_estimation": {"imu_yaw_bias_radps": 0.012}}
        )
        self.settings.merge_if_current.return_value = saved
        result = await self.service.apply(
            CalibrationApply(trial_ids=[trial.id, "repeat"])
        )
        self.settings.merge_if_current.assert_called_once_with(
            saved, self.config, calibration_step="imu_bias"
        )
        self.assertEqual(
            result.saved_config, {"pose_estimation": {"imu_yaw_bias_radps": 0.012}}
        )
        self.assertFalse(self.config.pose_estimation.enabled)

    async def test_apply_failure_releases_arming_gate(self):
        session = self.session("imu_bias")
        trial = self.service._trial(session, True, "Measured", gyro_bias_radps=0.012)
        self.service.trials = [trial, trial.model_copy(update={"id": "repeat"})]
        motion = MagicMock(spec=MotionControlService)
        motion.set_mode = AsyncMock()
        self.service.motion = motion
        self.settings.merge_if_current.side_effect = RuntimeError("disk full")
        with self.assertRaisesRegex(RuntimeError, "disk full"):
            await self.service.apply(CalibrationApply(trial_ids=[trial.id, "repeat"]))
        self.assertFalse(motion.calibration_active)
        motion.set_mode.assert_awaited_once_with(RobotMode.DISARMED)

    def test_stopping_review_includes_body_response_margin_and_rejects_lower_speed(
        self,
    ):
        self.config.motion_control.max_forward_speed_mps = 0.2
        self.config.motion_control.max_reverse_speed_mps = 0.2
        self.config.lidar_safety.stop_distance_m = 1
        self.config.lidar_safety.slow_distance_m = 2
        trials = []
        for direction in ("forward", "reverse"):
            session = self.session("stopping", direction=direction)
            for n in range(2):
                trials.append(
                    self.service._trial(
                        session,
                        True,
                        "Measured",
                        mean_speed_mps=0.2,
                        stopping_distance_m=0.03,
                    ).model_copy(update={"id": f"{direction}{n}"})
                )
        self.service.trials = trials
        selection = CalibrationApply(trial_ids=[t.id for t in trials])
        self.assertEqual(
            self.service.proposed_update(selection),
            {"lidar_safety": {"stop_distance_m": 1, "slow_distance_m": 2}},
        )
        trials[0].mean_speed_mps = 0.1
        with self.assertRaisesRegex(CalibrationError, "highest calibrated speed"):
            self.service.proposed_update(selection)

    async def test_failed_hardware_stop_latches_calibration_fault(self):
        status = await self.service.start(
            CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
        )
        assert status.session_id
        self.hardware.release_calibration = MagicMock(
            side_effect=RuntimeError("bus failed")
        )
        with self.assertRaisesRegex(CalibrationError, "stop could not be confirmed"):
            await self.service.cancel(status.session_id)
        with self.assertRaisesRegex(CalibrationError, "Disconnect motor power"):
            await self.service.start(
                CalibrationStart(kind="wheel_distance", clear_path_confirmed=True)
            )

    def test_steering_table_detects_reversed_sensor_direction(self):
        self.config.localization_sensors.steering.center_angle_deg = 180
        session = self.session("steering_range")
        self.service.trials = [
            self.service._trial(
                session,
                True,
                "Measured",
                sensor_angle_deg=180 - angle,
                steering_degrees=angle,
            ).model_copy(update={"id": str(angle)})
            for angle in (-20, 0, 20)
        ]
        update = self.service.proposed_update(
            CalibrationApply(trial_ids=[t.id for t in self.service.trials])
        )
        steering = update["localization_sensors"]["steering"]
        PartialHardwareConfig.model_validate(update)
        self.assertTrue(steering["invert_direction"])
        self.assertAlmostEqual(
            steering["calibration_points"][0]["wheel_angle_rad"], math.radians(-20)
        )
        self.assertEqual(steering["calibration_points"][0]["sensor_offset_deg"], -20)

    def test_steering_center_handles_reversed_servo(self):
        for reverse, mode, expected in (
            (False, "sum", 5),
            (True, "sum", -5),
            (False, "negative", -5),
            (True, "negative", 5),
        ):
            self.config.steering_servo = self.config.steering_servo.model_validate(
                {
                    **self.config.steering_servo.model_dump(),
                    "reverse": reverse,
                    "calibration_mode": mode,
                    "calibration_offset": 0,
                }
            )
            session = self.session("steering_center")
            self.service.trials = [
                self.service._trial(
                    session, True, "Measured", sensor_angle_deg=180, steering_degrees=5
                )
            ]
            update = self.service.proposed_update(
                CalibrationApply(trial_ids=[session.id])
            )
            self.assertEqual(update["steering_servo"]["calibration_offset"], expected)
            PartialHardwareConfig.model_validate(update)

    def test_distance_fit_handles_irregular_timestamps(self):
        self.assertAlmostEqual(
            fit_speed([(10, 3), (10.1, 2.98), (10.7, 2.86), (11, 2.8)]), -0.2
        )
