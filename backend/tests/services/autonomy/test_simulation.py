import asyncio
import math
import unittest

from app.services.autonomy import (
    AckermannOdometryConfig,
    AckermannOdometryEstimator,
    AckermannOdometryService,
    AckermannSimulationConfig,
    AckermannSimulationPlant,
    ActuatorCommand,
    CoherentSimulationService,
    CoherentSimulationSupervisor,
    MotionSource,
    TopicBus,
)
from app.services.autonomy.topics import (
    ENCODER_STATE,
    IMU_DATA,
    MOTION_COMMANDED,
    ODOMETRY,
    SIMULATION_STATE,
    STEERING_STATE,
)


def command(
    *,
    speed_mps: float,
    steering_rad: float = 0.0,
    timestamp_ns: int = 1_000_000_000,
) -> ActuatorCommand:
    return ActuatorCommand(
        source=MotionSource.AUTONOMY,
        linear_speed_mps=speed_mps,
        steering_angle_rad=steering_rad,
        selected_monotonic_ns=timestamp_ns,
        command_id="simulation-test",
    )


class AckermannSimulationPlantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AckermannSimulationConfig(
            wheelbase_m=0.25,
            wheel_radius_m=0.03,
            encoder_ticks_per_revolution=4096,
            update_frequency_hz=100,
        )
        self.plant = AckermannSimulationPlant(self.config)

    def test_advances_straight_pose_and_encoder_from_one_distance(self) -> None:
        state = self.plant.advance(command(speed_mps=1), dt_seconds=0.01)

        expected_ticks = round(0.01 / (2 * math.pi * 0.03) * 4096)
        self.assertAlmostEqual(state.x_m, 0.01)
        self.assertAlmostEqual(state.y_m, 0)
        self.assertAlmostEqual(state.yaw_rad, 0)
        self.assertEqual(state.encoder_ticks, expected_ticks)
        self.assertAlmostEqual(state.longitudinal_acceleration_mps2, 100)

    def test_arc_uses_midpoint_integration_and_ackermann_yaw_rate(self) -> None:
        steering = math.radians(-20)
        state = self.plant.advance(
            command(speed_mps=0.5, steering_rad=steering),
            dt_seconds=0.02,
        )

        expected_yaw_rate = -0.5 / 0.25 * math.tan(steering)
        expected_delta_yaw = expected_yaw_rate * 0.02
        self.assertAlmostEqual(state.yaw_rate_radps, expected_yaw_rate)
        self.assertAlmostEqual(state.yaw_rad, expected_delta_yaw)
        self.assertAlmostEqual(state.x_m, 0.01 * math.cos(expected_delta_yaw / 2))
        self.assertAlmostEqual(state.y_m, 0.01 * math.sin(expected_delta_yaw / 2))
        self.assertAlmostEqual(
            state.lateral_acceleration_mps2,
            0.5 * expected_yaw_rate,
        )

    def test_reverse_motion_decrements_ticks_and_reverses_yaw(self) -> None:
        state = self.plant.advance(
            command(speed_mps=-0.5, steering_rad=math.radians(-15)),
            dt_seconds=0.02,
        )

        self.assertLess(state.encoder_ticks, 0)
        self.assertLess(state.yaw_rad, 0)
        self.assertLess(state.linear_speed_mps, 0)

    def test_reset_restores_requested_ground_truth(self) -> None:
        self.plant.advance(command(speed_mps=1), dt_seconds=0.1)

        state = self.plant.reset(x_m=2, y_m=-1, yaw_rad=math.pi)

        self.assertEqual(state.x_m, 2)
        self.assertEqual(state.y_m, -1)
        self.assertAlmostEqual(state.yaw_rad, -math.pi)
        self.assertEqual(state.linear_speed_mps, 0)
        self.assertEqual(state.encoder_ticks, 0)


class CoherentSimulationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.config = AckermannSimulationConfig(
            wheelbase_m=0.25,
            wheel_radius_m=0.03,
            encoder_ticks_per_revolution=4096,
            update_frequency_hz=100,
            command_timeout_seconds=0.25,
        )
        self.bus = TopicBus()
        self.service = CoherentSimulationService(
            self.bus,
            AckermannSimulationPlant(self.config),
        )

    async def asyncTearDown(self) -> None:
        await self.service.stop()

    async def test_one_step_publishes_synchronized_coherent_messages(self) -> None:
        timestamp = 1_000_000_000
        self.bus.publish(
            MOTION_COMMANDED,
            command(
                speed_mps=0.5,
                steering_rad=math.radians(20),
                timestamp_ns=timestamp,
            ),
        )

        truth = self.service.step_once(timestamp_ns=timestamp + 10_000_000)
        steering = self.bus.latest(STEERING_STATE)
        encoder = self.bus.latest(ENCODER_STATE)
        imu = self.bus.latest(IMU_DATA)
        retained_truth = self.bus.latest(SIMULATION_STATE)

        self.assertIsNotNone(steering)
        self.assertIsNotNone(encoder)
        self.assertIsNotNone(imu)
        assert steering is not None
        assert encoder is not None
        assert imu is not None
        self.assertEqual(retained_truth, truth)
        self.assertEqual(
            {
                steering.header.timestamp_monotonic_ns,
                encoder.header.timestamp_monotonic_ns,
                imu.header.timestamp_monotonic_ns,
                truth.header.timestamp_monotonic_ns,
            },
            {timestamp + 10_000_000},
        )
        self.assertEqual(
            {
                steering.header.sequence,
                encoder.header.sequence,
                imu.header.sequence,
                truth.header.sequence,
            },
            {1},
        )
        self.assertAlmostEqual(
            steering.measured_angle_rad or 0,
            truth.steering_angle_rad,
        )
        self.assertAlmostEqual(imu.yaw_rad or 0, truth.yaw_rad)
        self.assertAlmostEqual(
            imu.angular_velocity_z_radps,
            truth.yaw_rate_radps,
        )
        self.assertEqual(encoder.left, encoder.right)
        self.assertEqual(
            encoder.left.ticks if encoder.left else None, truth.encoder_ticks
        )

    async def test_stale_command_watchdog_stops_without_reusing_speed(self) -> None:
        timestamp = 1_000_000_000
        self.bus.publish(
            MOTION_COMMANDED,
            command(speed_mps=0.5, steering_rad=0.2, timestamp_ns=timestamp),
        )
        moving = self.service.step_once(timestamp_ns=timestamp + 10_000_000)

        stopped = self.service.step_once(timestamp_ns=timestamp + 500_000_000)

        self.assertEqual(stopped.linear_speed_mps, 0)
        self.assertEqual(stopped.x_m, moving.x_m)
        self.assertEqual(stopped.y_m, moving.y_m)
        self.assertEqual(stopped.encoder_ticks, moving.encoder_ticks)
        self.assertEqual(stopped.steering_angle_rad, moving.steering_angle_rad)

    async def test_encoder_rounding_preserves_cumulative_small_movements(self) -> None:
        timestamp = 1_000_000_000
        self.bus.publish(
            MOTION_COMMANDED,
            command(speed_mps=0.01, timestamp_ns=timestamp),
        )

        deltas = []
        truth = None
        for step in range(1, 21):
            truth = self.service.step_once(timestamp_ns=timestamp + step * 10_000_000)
            encoder = self.bus.latest(ENCODER_STATE)
            assert encoder is not None
            assert encoder.left is not None
            deltas.append(encoder.left.delta_ticks)

        self.assertIsNotNone(truth)
        assert truth is not None
        self.assertEqual(sum(deltas), truth.encoder_ticks)
        self.assertGreater(truth.encoder_ticks, 0)

    async def test_async_lifecycle_publishes_and_stops_cleanly(self) -> None:
        output = self.bus.subscribe(SIMULATION_STATE, replay_latest=False)

        self.service.start()
        message = await asyncio.wait_for(output.get(), timeout=0.5)
        await self.service.stop()

        self.assertEqual(message.header.sequence, 1)
        self.assertFalse(self.service.running)
        self.assertIsNone(self.service.last_error)

    async def test_native_sensor_topics_drive_existing_odometry_service(self) -> None:
        odometry_service = AckermannOdometryService(
            self.bus,
            AckermannOdometryEstimator(
                AckermannOdometryConfig(
                    wheelbase_m=self.config.wheelbase_m,
                    wheel_radius_m=self.config.wheel_radius_m,
                    encoder_ticks_per_revolution=(
                        self.config.encoder_ticks_per_revolution
                    ),
                )
            ),
        )
        output = self.bus.subscribe(ODOMETRY, replay_latest=False)
        timestamp = 1_000_000_000
        steering = math.radians(-20)
        self.bus.publish(
            MOTION_COMMANDED,
            command(
                speed_mps=0.5,
                steering_rad=steering,
                timestamp_ns=timestamp,
            ),
        )
        odometry_service.start()
        try:
            self.service.step_once(timestamp_ns=timestamp + 10_000_000)
            first = await asyncio.wait_for(output.get(), timeout=0.2)
            truth = self.service.step_once(timestamp_ns=timestamp + 20_000_000)
            second = await asyncio.wait_for(output.get(), timeout=0.2)
        finally:
            await odometry_service.stop()

        expected_step_yaw = (
            -0.5
            / self.config.wheelbase_m
            * math.tan(steering)
            * self.config.update_period_seconds
        )
        self.assertEqual(first.x_m, 0)
        self.assertGreater(second.x_m, 0)
        self.assertAlmostEqual(second.yaw_rad, expected_step_yaw, places=3)
        self.assertAlmostEqual(truth.yaw_rad, expected_step_yaw * 2)
        self.assertAlmostEqual(second.linear_speed_mps, 0.5, places=2)


class CoherentSimulationSupervisorTests(unittest.IsolatedAsyncioTestCase):
    def make_service(self, bus: TopicBus) -> CoherentSimulationService:
        return CoherentSimulationService(
            bus,
            AckermannSimulationPlant(
                AckermannSimulationConfig(
                    wheelbase_m=0.25,
                    wheel_radius_m=0.03,
                    encoder_ticks_per_revolution=4096,
                    update_frequency_hz=100,
                )
            ),
            initial_x_m=2.0,
            initial_y_m=-1.0,
            initial_yaw_rad=0.25,
        )

    async def test_hot_reconfigure_replaces_running_service(self) -> None:
        bus = TopicBus()
        first = self.make_service(bus)
        second = self.make_service(bus)
        supervisor = CoherentSimulationSupervisor(first)

        await supervisor.start()
        await asyncio.sleep(0.02)
        await supervisor.reconfigure(second)

        self.assertFalse(first.running)
        self.assertTrue(second.running)
        self.assertIs(supervisor.service, second)

        await supervisor.reconfigure(None)

        self.assertFalse(second.running)
        self.assertFalse(supervisor.enabled)
        await supervisor.stop()

    async def test_reset_restores_configured_initial_pose_and_restarts(self) -> None:
        bus = TopicBus()
        service = self.make_service(bus)
        supervisor = CoherentSimulationSupervisor(service)
        await supervisor.start()
        await asyncio.sleep(0.02)

        reset_state = await supervisor.reset()

        self.assertEqual(reset_state.x_m, 2.0)
        self.assertEqual(reset_state.y_m, -1.0)
        self.assertEqual(reset_state.yaw_rad, 0.25)
        self.assertTrue(supervisor.running)
        self.assertEqual(service.published_updates, 0)
        await supervisor.stop()


if __name__ == "__main__":
    unittest.main()
