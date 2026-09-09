import math
import unittest
from dataclasses import dataclass

from app.schemas.autonomy import (
    EncoderState,
    LocalizationPose2D,
    Odometry2D,
    SimulationState,
)
from app.services.autonomy import (
    AckermannOdometryConfig,
    AckermannOdometryEstimator,
    AckermannSimulationConfig,
    AckermannSimulationPlant,
    CoherentSimulationService,
    LidarSafetyEvaluator,
    LidarSafetyService,
    LidarSafetyZone,
    MotionArbiter,
    MotionIntent,
    MotionLimits,
    MotionSource,
    PoseEstimator,
    PoseEstimatorConfig,
    RaycastLidarConfig,
    RobotMode,
    SimulationSensorImperfections,
    TopicBus,
    WorldLidarRaycaster,
    build_simulation_world,
)
from app.services.autonomy.clock import ReplayClock
from app.services.autonomy.odometry import OdometryInputError
from app.services.autonomy.topics import (
    ENCODER_STATE,
    IMU_DATA,
    LIDAR_SCAN,
    MOTION_COMMANDED,
    SIMULATION_STATE,
    STEERING_STATE,
)
from tests.services.autonomy.fault_scenarios import (
    DeliveryFault,
    SensorDelivery,
    advance_step,
)
from tests.services.autonomy.test_simulation import command
from tests.services.autonomy.test_lidar_safety import ConstraintRecorder
from tests.services.autonomy.test_occupancy_scan_matching import ObservedMapFixture
from tests.services.autonomy.test_scan_matching import pose


@dataclass(frozen=True)
class DriveReport:
    poses: tuple[LocalizationPose2D, ...]
    truth: SimulationState
    dropped: int
    delayed: int
    imu_used: int
    imu_rejected: int
    odometry_rejected: int

    @property
    def position_error_m(self) -> float:
        pose = self.poses[-1]
        return math.hypot(pose.x_m - self.truth.x_m, pose.y_m - self.truth.y_m)


async def drive(
    faults: tuple[DeliveryFault, ...] = (),
    *,
    noisy: bool = False,
    steering_rad: float = 0,
) -> DriveReport:
    source, measured = TopicBus(), TopicBus()
    clock = ReplayClock()
    delivery = SensorDelivery(source, measured, faults)
    world = build_simulation_world("empty_room", width_m=6, height_m=6)
    simulation = CoherentSimulationService(
        source,
        AckermannSimulationPlant(
            AckermannSimulationConfig(
                wheelbase_m=0.25,
                wheel_radius_m=0.03,
                encoder_ticks_per_revolution=4096,
                update_frequency_hz=50,
            )
        ),
        monotonic_ns=clock.monotonic_ns,
        lidar_raycaster=WorldLidarRaycaster(
            world,
            RaycastLidarConfig(
                frame_id="laser",
                sensor_x_m=0,
                sensor_y_m=0,
                sensor_yaw_rad=0,
                range_min_m=0.05,
                range_max_m=12,
                angular_resolution_deg=10,
            ),
        ),
        sensor_imperfections=SimulationSensorImperfections(
            enabled=noisy, random_seed=123
        ),
    )
    odometry = AckermannOdometryEstimator(
        AckermannOdometryConfig(
            wheelbase_m=0.25,
            wheel_radius_m=0.03,
            encoder_ticks_per_revolution=4096,
        )
    )
    estimator = PoseEstimator(PoseEstimatorConfig())
    poses: list[LocalizationPose2D] = []
    used = rejected = invalid_odometry = 0
    previous_encoder: EncoderState | None = None
    try:
        for step in range(151):
            now = advance_step(clock, step)
            source.publish(
                MOTION_COMMANDED,
                command(
                    speed_mps=0.2 if step else 0,
                    steering_rad=steering_rad,
                    timestamp_ns=now,
                ),
            )
            simulation.step_once(timestamp_ns=now)
            delivery.step(step)
            encoder, steering = measured.latest(ENCODER_STATE), measured.latest(
                STEERING_STATE
            )
            if encoder is None or steering is None or encoder is previous_encoder:
                continue
            previous_encoder = encoder
            try:
                result = estimator.update(
                    odometry.update(encoder, steering), imu=measured.latest(IMU_DATA)
                )
            except OdometryInputError:
                invalid_odometry += 1
                continue
            poses.append(result.pose)
            used += int(result.imu_used)
            rejected += int(result.imu_rejection is not None)
        assert measured.latest(SIMULATION_STATE) is None
        assert measured.latest(MOTION_COMMANDED) is None
        assert simulation.latest is not None
        return DriveReport(
            tuple(poses),
            simulation.latest,
            delivery.dropped,
            delivery.delayed,
            used,
            rejected,
            invalid_odometry,
        )
    finally:
        delivery.close()
        source.close()
        measured.close()


class SensorFaultScenarios(unittest.IsolatedAsyncioTestCase):
    async def test_lidar_outage_and_delayed_backlog_keep_arbiter_stopped(self) -> None:
        for fault in (
            DeliveryFault(LIDAR_SCAN.name, 10, 50, drop=True),
            DeliveryFault(LIDAR_SCAN.name, 10, 50, delay_steps=30),
        ):
            with self.subTest(fault=fault):
                source, measured = TopicBus(), TopicBus()
                clock = ReplayClock()
                advance_step(clock, 0)
                delivery = SensorDelivery(source, measured, (fault,))
                constraints = ConstraintRecorder()
                safety = LidarSafetyService(
                    measured,
                    constraints,
                    LidarSafetyEvaluator(
                        LidarSafetyZone(
                            front_half_angle_rad=0.5,
                            stop_distance_m=0.3,
                            slow_distance_m=0.8,
                            max_forward_speed_mps=1,
                            max_reverse_speed_mps=0.5,
                            min_obstacle_points=1,
                        )
                    ),
                    scan_timeout_seconds=0.2,
                    clock=clock,
                )
                arbiter = MotionArbiter(
                    MotionLimits(
                        max_forward_speed_mps=1,
                        max_reverse_speed_mps=0.5,
                        max_abs_steering_angle_rad=0.6,
                    ),
                    clock,
                )
                arbiter.submit(
                    MotionIntent(
                        command_id="fault-drive",
                        source=MotionSource.AUTONOMY,
                        sequence=1,
                        mode_generation=0,
                        linear_speed_mps=0.2,
                        steering_angle_rad=0,
                        created_monotonic_ns=clock.monotonic_ns(),
                        expires_monotonic_ns=10_000_000_000,
                    ),
                    mode=RobotMode.AUTONOMOUS,
                    mode_generation=0,
                )
                raycaster = WorldLidarRaycaster(
                    build_simulation_world("empty_room", width_m=6, height_m=6),
                    RaycastLidarConfig(
                        frame_id="laser",
                        sensor_x_m=0,
                        sensor_y_m=0,
                        sensor_yaw_rad=0,
                        range_min_m=0.05,
                        range_max_m=12,
                        angular_resolution_deg=10,
                    ),
                )
                speeds = []
                previous = None
                try:
                    for step in range(91):
                        now = advance_step(clock, step)
                        if step % 5 == 0:
                            source.publish(
                                LIDAR_SCAN,
                                raycaster.scan(
                                    base_x_m=0,
                                    base_y_m=0,
                                    base_yaw_rad=0,
                                    timestamp_ns=now,
                                    sequence=step + 1,
                                ),
                            )
                        delivery.step(step)
                        scan = measured.latest(LIDAR_SCAN)
                        if scan is not None and scan is not previous:
                            safety.process_scan(scan)
                            previous = scan
                        safety.check_freshness()
                        speeds.append(
                            arbiter.resolve(
                                mode=RobotMode.AUTONOMOUS,
                                mode_generation=0,
                                constraints=constraints.constraints.values(),
                            ).command.linear_speed_mps
                        )
                    self.assertEqual(speeds[5], 0.2)
                    self.assertTrue(all(speed == 0 for speed in speeds[16:50]))
                    self.assertEqual(speeds[-1], 0.2)
                finally:
                    delivery.close()
                    source.close()
                    measured.close()

    async def test_clean_straight_and_arc_match_simulated_truth(self) -> None:
        for steering in (0, math.radians(-15), math.radians(15)):
            with self.subTest(steering=steering):
                report = await drive(steering_rad=steering)
                self.assertLess(report.position_error_m, 0.002)
                self.assertEqual(report.imu_used, 150)
                self.assertEqual(report.odometry_rejected, 0)

    async def test_seeded_noise_and_delivery_faults_are_repeatable(self) -> None:
        faults = (
            DeliveryFault(IMU_DATA.name, 30, 60, delay_steps=15),
            DeliveryFault(LIDAR_SCAN.name, 70, 90, drop=True),
        )
        first = await drive(faults, noisy=True, steering_rad=-0.2)
        second = await drive(faults, noisy=True, steering_rad=-0.2)
        self.assertEqual(first, second)
        self.assertGreater(first.delayed, 0)
        self.assertGreater(first.dropped, 0)
        self.assertLess(first.position_error_m, 0.1)

    async def test_imu_outage_and_latency_fall_back_to_wheels_then_recover(
        self,
    ) -> None:
        for fault in (
            DeliveryFault(IMU_DATA.name, 30, 70, drop=True),
            DeliveryFault(IMU_DATA.name, 30, 70, delay_steps=15),
        ):
            with self.subTest(fault=fault):
                report = await drive((fault,), steering_rad=-0.2)
                self.assertGreater(report.imu_rejected, 20)
                self.assertEqual(report.poses[60].fusion_mode, "wheel")
                self.assertEqual(report.poses[-1].fusion_mode, "wheel_imu")
                self.assertLess(report.position_error_m, 0.005)

    async def test_dropped_encoder_messages_preserve_cumulative_straight_distance(
        self,
    ) -> None:
        baseline = await drive()
        report = await drive((DeliveryFault(ENCODER_STATE.name, 30, 60, drop=True),))
        self.assertEqual(report.dropped, 30)
        self.assertEqual(len(report.poses), 121)
        self.assertLess(report.position_error_m, 0.002)
        self.assertAlmostEqual(
            report.poses[-1].x_m, baseline.poses[-1].x_m, delta=0.002
        )

    async def test_steering_outage_rejects_old_geometry_then_recovers(self) -> None:
        report = await drive((DeliveryFault(STEERING_STATE.name, 30, 70, drop=True),))
        self.assertGreater(report.odometry_rejected, 20)
        self.assertEqual(report.poses[-1].header.timestamp_monotonic_ns, 4_000_000_000)

    async def test_delayed_encoder_frames_do_not_use_future_steering(self) -> None:
        report = await drive(
            (DeliveryFault(ENCODER_STATE.name, 30, 70, delay_steps=15),)
        )
        self.assertGreater(report.odometry_rejected, 20)
        self.assertLess(report.position_error_m, 0.002)
        self.assertEqual(report.poses[-1].header.timestamp_monotonic_ns, 4_000_000_000)


class FrozenMapCorrectionFaultScenarios(ObservedMapFixture, unittest.TestCase):
    def test_late_alignment_is_rejected_without_retimestamping_and_next_one_recovers(
        self,
    ) -> None:
        prior = pose(0.9, 0.23, 0.31)
        estimator = PoseEstimator(PoseEstimatorConfig())
        initial = Odometry2D(
            header=prior.header,
            x_m=prior.x_m,
            y_m=prior.y_m,
            yaw_rad=prior.yaw_rad,
            linear_speed_mps=0,
            yaw_rate_radps=0,
        )
        estimator.update(initial)
        alignment = self.observed_matcher.match(self.scan(), prior, sequence=1)
        self.assertTrue(alignment.accepted)
        current = initial.model_copy(
            update={
                "header": initial.header.model_copy(
                    update={"sequence": 2, "timestamp_monotonic_ns": 1_400_000_000}
                )
            }
        )
        delayed = estimator.update(current, observation=alignment.observation)
        self.assertFalse(delayed.correction_applied)
        self.assertEqual(delayed.correction_rejection, "pose observation is stale")
        self.assertAlmostEqual(delayed.pose.x_m, prior.x_m)
        # A new scan has a new acquisition time; never relabel the delayed one.
        fresh_scan = self.raycaster.scan(
            base_x_m=0.8,
            base_y_m=0.3,
            base_yaw_rad=0.25,
            timestamp_ns=1_410_000_000,
            sequence=2,
        )
        fresh = self.observed_matcher.match(fresh_scan, delayed.pose, sequence=2)
        current = current.model_copy(
            update={
                "header": current.header.model_copy(
                    update={"sequence": 3, "timestamp_monotonic_ns": 1_420_000_000}
                )
            }
        )
        recovered = estimator.update(current, observation=fresh.observation)
        self.assertTrue(recovered.correction_applied)
        self.assertLess(abs(recovered.pose.x_m - 0.8), abs(delayed.pose.x_m - 0.8))
