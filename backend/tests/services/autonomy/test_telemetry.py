import asyncio
import json
import math
import unittest
from typing import Any, Dict, List

from app.schemas.autonomy import (
    ImuData,
    LaserScan,
    LocalizationPose2D,
    MessageHeader,
    SimulationState,
)
from app.services.autonomy import (
    SensorTelemetryStreamer,
    TopicBus,
    make_telemetry_envelope,
    parse_telemetry_channels,
)
from app.services.autonomy.topics import IMU_DATA


def header(sequence: int = 1) -> MessageHeader:
    return MessageHeader(
        sequence=sequence,
        frame_id="sensor",
        timestamp_monotonic_ns=sequence * 100,
    )


class TestTelemetryContract(unittest.TestCase):
    def test_lidar_infinity_is_standard_json_null(self) -> None:
        scan = LaserScan(
            header=header(),
            angle_min_rad=0,
            angle_max_rad=math.pi,
            angle_increment_rad=math.pi,
            range_min_m=0.1,
            range_max_m=10,
            ranges_m=(1.0, math.inf),
        )

        envelope = make_telemetry_envelope("lidar", scan)
        data = envelope.model_dump(mode="json")

        self.assertEqual(data["topic"], "/lidar/scan")
        self.assertEqual(data["payload"]["ranges_m"], [1.0, None])
        json.dumps(data, allow_nan=False)

    def test_channel_parser_rejects_unknown_and_deduplicates(self) -> None:
        self.assertEqual(
            parse_telemetry_channels("imu, lidar,imu"),
            ("imu", "lidar"),
        )
        with self.assertRaisesRegex(ValueError, "unknown telemetry channel"):
            parse_telemetry_channels("camera")

    def test_simulation_truth_uses_the_existing_telemetry_contract(self) -> None:
        state = SimulationState(
            header=header(),
            x_m=1,
            y_m=2,
            yaw_rad=0.3,
            linear_speed_mps=0.2,
            steering_angle_rad=-0.1,
            yaw_rate_radps=0.05,
            longitudinal_acceleration_mps2=0,
            lateral_acceleration_mps2=0.01,
            encoder_ticks=42,
            collision=False,
        )

        envelope = make_telemetry_envelope("simulation", state)

        self.assertEqual(envelope.topic, "/simulation/state")
        self.assertEqual(envelope.payload, state)

    def test_localization_pose_uses_canonical_pose_topic(self) -> None:
        pose = LocalizationPose2D(
            header=header(),
            x_m=1,
            y_m=2,
            yaw_rad=0.1,
            linear_speed_mps=0.2,
            yaw_rate_radps=0.03,
            position_variance_m2=0.01,
            yaw_variance_rad2=0.02,
            fusion_mode="wheel_imu",
        )

        envelope = make_telemetry_envelope("localization", pose)

        self.assertEqual(envelope.topic, "/pose")
        self.assertEqual(envelope.payload, pose)


class TestTelemetryStreamer(unittest.IsolatedAsyncioTestCase):
    async def test_streams_latest_values_and_releases_subscriptions(self) -> None:
        bus = TopicBus()
        imu = ImuData(
            header=header(),
            angular_velocity_z_radps=0.3,
            acceleration_x_mps2=1,
            acceleration_y_mps2=2,
            acceleration_z_mps2=3,
        )
        bus.publish(IMU_DATA, imu)
        output: List[Dict[str, Any]] = []
        received = asyncio.Event()

        async def sink(message: Dict[str, Any]) -> None:
            output.append(message)
            received.set()

        streamer = SensorTelemetryStreamer(
            bus,
            channels=("imu",),
            max_rate_hz=30,
        )
        task = asyncio.create_task(streamer.stream(sink))
        await asyncio.wait_for(received.wait(), timeout=1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        self.assertEqual(output[0]["channel"], "imu")
        self.assertEqual(output[0]["payload"]["angular_velocity_z_radps"], 0.3)
        self.assertEqual(bus.stats(IMU_DATA).subscribers, 0)

    async def test_slow_stream_keeps_only_the_latest_topic_value(self) -> None:
        bus = TopicBus()
        output: List[Dict[str, Any]] = []
        second_message = asyncio.Event()

        async def sink(message: Dict[str, Any]) -> None:
            output.append(message)
            if len(output) == 2:
                second_message.set()

        streamer = SensorTelemetryStreamer(
            bus,
            channels=("imu",),
            max_rate_hz=10,
        )
        task = asyncio.create_task(streamer.stream(sink))
        await asyncio.sleep(0)
        bus.publish(
            IMU_DATA,
            ImuData(
                header=header(1),
                angular_velocity_z_radps=1,
                acceleration_x_mps2=0,
                acceleration_y_mps2=0,
                acceleration_z_mps2=0,
            ),
        )
        while not output:
            await asyncio.sleep(0)
        for sequence in range(2, 5):
            bus.publish(
                IMU_DATA,
                ImuData(
                    header=header(sequence),
                    angular_velocity_z_radps=float(sequence),
                    acceleration_x_mps2=0,
                    acceleration_y_mps2=0,
                    acceleration_z_mps2=0,
                ),
            )
        await asyncio.wait_for(second_message.wait(), timeout=1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        self.assertEqual(output[-1]["payload"]["header"]["sequence"], 4)
        self.assertGreaterEqual(bus.stats(IMU_DATA).dropped_messages, 2)


if __name__ == "__main__":
    unittest.main()
