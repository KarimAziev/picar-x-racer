import asyncio
import math
import unittest
from unittest.mock import patch

from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import STEERING_POSITION, STEERING_STATE

from app.services.autonomy.steering_feedback import (
    SteeringAngleCalibration,
    SteeringCalibrationPoint,
    SteeringFeedbackService,
)
from robot_hat import MockAngularPosition


class TestSteeringAngleCalibration(unittest.TestCase):
    def test_wraps_absolute_bearing_to_signed_wheel_angle(self) -> None:
        calibration = SteeringAngleCalibration(center_angle_deg=180.0)

        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(170.0),
            math.radians(-10.0),
        )
        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(190.0),
            math.radians(10.0),
        )

    def test_applies_direction_and_mechanical_ratio(self) -> None:
        calibration = SteeringAngleCalibration(
            center_angle_deg=5.0,
            invert_direction=True,
            wheel_degrees_per_sensor_degree=0.5,
        )

        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(355.0),
            math.radians(5.0),
        )

    def test_interpolates_asymmetric_linkage_calibration(self) -> None:
        calibration = SteeringAngleCalibration(
            center_angle_deg=180.0,
            points=(
                SteeringCalibrationPoint(-20.0, math.radians(-30.0)),
                SteeringCalibrationPoint(0.0, 0.0),
                SteeringCalibrationPoint(10.0, math.radians(25.0)),
            ),
        )

        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(185.0),
            math.radians(12.5),
        )
        with self.assertRaisesRegex(ValueError, "outside"):
            calibration.to_wheel_angle_rad(200.0)

    def test_rejects_ambiguous_or_unordered_calibration(self) -> None:
        with self.assertRaises(ValueError):
            SteeringAngleCalibration(
                center_angle_deg=0.0,
                points=(SteeringCalibrationPoint(0.0, 0.0),),
            )
        with self.assertRaises(ValueError):
            SteeringAngleCalibration(
                center_angle_deg=0.0,
                points=(
                    SteeringCalibrationPoint(1.0, 0.1),
                    SteeringCalibrationPoint(1.0, 0.2),
                ),
            )


class TestSteeringFeedbackService(unittest.IsolatedAsyncioTestCase):
    async def test_publishes_position_without_motion_control(self) -> None:
        bus = TopicBus()
        subscription = bus.subscribe(STEERING_POSITION, max_queue_size=1)
        sensor = MockAngularPosition(initial_angle_degrees=190.0)
        service = SteeringFeedbackService(
            lambda: sensor,
            SteeringAngleCalibration(center_angle_deg=180.0),
            sample_frequency_hz=100,
            topic_bus=bus,
        )
        await service.start()
        try:
            first = await asyncio.wait_for(subscription.get(), timeout=1)
            second = await asyncio.wait_for(subscription.get(), timeout=1)
            self.assertEqual(first.sensor_angle_deg, 190.0)
            self.assertAlmostEqual(first.wheel_angle_rad, math.radians(10))
            self.assertGreater(second.header.sequence, first.header.sequence)
            self.assertGreater(
                second.header.timestamp_monotonic_ns,
                first.header.timestamp_monotonic_ns,
            )
            self.assertIsNone(bus.latest(STEERING_STATE))
            self.assertTrue(service.status.running)
            self.assertGreaterEqual(service.status.published_messages, 2)
            self.assertEqual(
                service.status.last_timestamp_monotonic_ns,
                second.header.timestamp_monotonic_ns,
            )
        finally:
            await service.stop()
            subscription.close()
        self.assertFalse(service.status.running)
        self.assertFalse(sensor.read_health().available)

    async def test_startup_error_is_visible_in_diagnostics(self) -> None:
        sensor = MockAngularPosition()
        service = SteeringFeedbackService(
            lambda: sensor,
            SteeringAngleCalibration(center_angle_deg=0),
            sample_frequency_hz=100,
            topic_bus=TopicBus(),
        )
        with patch.object(
            sensor, "initialize", side_effect=RuntimeError("SPI unavailable")
        ):
            with self.assertRaisesRegex(RuntimeError, "SPI unavailable"):
                await service.start()
        self.assertEqual(service.status.error, "SPI unavailable")
        self.assertFalse(service.status.running)
        self.assertEqual(service.status.published_messages, 0)
        self.assertFalse(sensor.read_health().available)

    async def test_sampling_error_clears_feedback_and_closes_sensor(self) -> None:
        sensor = MockAngularPosition()
        bus = TopicBus()
        service = SteeringFeedbackService(
            lambda: sensor,
            SteeringAngleCalibration(center_angle_deg=0),
            sample_frequency_hz=100,
            topic_bus=bus,
        )

        async def wait_until_stopped() -> None:
            while service.running:
                await asyncio.sleep(0.001)

        with patch.object(
            sensor, "read_angle", side_effect=RuntimeError("Magnet too weak")
        ):
            await service.start()
            await asyncio.wait_for(wait_until_stopped(), timeout=1)
        self.assertEqual(service.status.error, "Magnet too weak")
        self.assertIsNone(service.latest)
        self.assertIsNone(bus.latest(STEERING_POSITION))
        self.assertFalse(sensor.read_health().available)
        await service.stop()

    async def test_samples_and_calibrates_mock_position(self) -> None:
        sensor = MockAngularPosition(initial_angle_degrees=190.0)
        service = SteeringFeedbackService(
            lambda: sensor,
            SteeringAngleCalibration(center_angle_deg=180.0),
            sample_frequency_hz=100,
        )

        await service.start()
        try:
            for _attempt in range(20):
                if service.latest is not None:
                    break
                await asyncio.sleep(0.005)
            sample = service.latest
            self.assertIsNotNone(sample)
            assert sample is not None
            self.assertAlmostEqual(sample.wheel_angle_rad, math.radians(10.0))
            self.assertIsNone(service.last_error)
        finally:
            await service.stop()

        self.assertFalse(sensor.read_health().available)
        self.assertIsNone(service.latest)


if __name__ == "__main__":
    unittest.main()
