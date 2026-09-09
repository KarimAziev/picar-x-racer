import json
import math
from pathlib import Path
import tempfile
import unittest

from app.schemas.autonomy import (
    MessageHeader,
    Odometry2D,
    LaserScan,
    MappingSessionStatus,
    MappingSessionState,
)
from app.services.autonomy.clock import ReplayClock
from app.services.autonomy.messages import ActuatorCommand, MotionSource
from app.services.autonomy.recording import AutonomyRecorder
from app.services.autonomy.replay import SessionReplay
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import (
    MOTION_COMMANDED,
    ODOMETRY,
    LIDAR_SCAN,
    MAPPING_SESSION,
)


def odometry(sequence: int) -> Odometry2D:
    return Odometry2D(
        header=MessageHeader(
            sequence=sequence,
            frame_id="odom",
            timestamp_monotonic_ns=1_000_000_000 + sequence * 100_000_000,
        ),
        x_m=sequence * 0.01,
        y_m=0,
        yaw_rad=0,
        linear_speed_mps=0.1,
        yaw_rate_radps=0,
    )


class RecordingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.bus = TopicBus()
        self.recorder = AutonomyRecorder(self.bus, self.directory)

    async def asyncTearDown(self) -> None:
        await self.recorder.stop()
        self.bus.close()
        self.temporary.cleanup()

    async def record_session(self) -> Path:
        await self.recorder.start(
            {
                "schema_version": 7,
                "pose_estimation": {},
                "unrelated_secret": "excluded",
            },
            {"git_commit": "test"},
        )
        for sequence in range(1, 4):
            self.bus.publish(ODOMETRY, odometry(sequence))
            self.bus.publish(
                MOTION_COMMANDED,
                ActuatorCommand(
                    source=MotionSource.MANUAL,
                    linear_speed_mps=0.1,
                    steering_angle_rad=0,
                    selected_monotonic_ns=sequence,
                ),
            )
        status = await self.recorder.stop()
        self.assertFalse(status.active)
        self.assertEqual(status.events_written, 6)
        self.assertEqual(status.dropped_events, 0)
        self.assertIsNone(status.error)
        return self.directory / f"{status.session_id}.jsonl"

    async def test_round_trip_keeps_order_and_recomputes_pose_without_live_commands(
        self,
    ) -> None:
        path = await self.record_session()
        lines = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertNotIn("unrelated_secret", lines[0]["config"])
        self.assertEqual([row["sequence"] for row in lines[1:-1]], list(range(6)))
        self.assertEqual(
            [row["topic"] for row in lines[1:-1]],
            [ODOMETRY.name, MOTION_COMMANDED.name] * 3,
        )
        live_commands = self.bus.subscribe(MOTION_COMMANDED, replay_latest=False)
        first = await SessionReplay(path).run()
        second = await SessionReplay(path).run()
        self.assertEqual(first, second)
        self.assertEqual(first["events"][ODOMETRY.name], 3)
        self.assertAlmostEqual(first["recomputed_final_pose"]["x_m"], 0.03)
        self.assertEqual(live_commands.pending_messages, 0)
        live_commands.close()

    async def test_overflow_is_counted_without_blocking_normal_subscribers(
        self,
    ) -> None:
        self.recorder = AutonomyRecorder(self.bus, self.directory, queue_size=2)
        normal = self.bus.subscribe(ODOMETRY, max_queue_size=10, replay_latest=False)
        await self.recorder.start({}, {})
        for sequence in range(5):
            self.bus.publish(ODOMETRY, odometry(sequence))
        status = await self.recorder.stop()
        self.assertEqual(normal.pending_messages, 5)
        self.assertEqual(status.dropped_events, 3)
        self.assertEqual(status.events_written, 2)
        replay = await SessionReplay(
            self.directory / f"{status.session_id}.jsonl"
        ).run()
        self.assertEqual(replay["dropped_events"], 3)
        normal.close()

    async def test_start_captures_retained_state_and_double_start_is_rejected(
        self,
    ) -> None:
        self.bus.publish(ODOMETRY, odometry(1))
        await self.recorder.start({}, {})
        with self.assertRaisesRegex(ValueError, "already active"):
            await self.recorder.start({}, {})
        status = await self.recorder.stop()
        rows = [
            json.loads(line)
            for line in (self.directory / f"{status.session_id}.jsonl")
            .read_text()
            .splitlines()
        ]
        self.assertTrue(rows[1]["snapshot"])
        self.assertEqual(
            rows[1]["payload"]["header"]["timestamp_monotonic_ns"], 1_100_000_000
        )

    async def test_file_limit_stops_recording_with_visible_failure(self) -> None:
        self.recorder = AutonomyRecorder(self.bus, self.directory, max_bytes=400)
        await self.recorder.start({}, {})
        self.bus.publish(ODOMETRY, odometry(1))
        status = await self.recorder.stop()
        self.assertFalse(status.active)
        self.assertIn("size limit", status.error or "")
        self.assertTrue((self.directory / f"{status.session_id}.jsonl").is_file())

    async def test_mapping_freeze_transitions_round_trip(self) -> None:
        await self.recorder.start({}, {})
        for state in (
            MappingSessionState.ACTIVE,
            MappingSessionState.PAUSED,
            MappingSessionState.IDLE,
        ):
            self.bus.publish(
                MAPPING_SESSION,
                MappingSessionStatus(
                    enabled=True,
                    state=state,
                    has_map=True,
                    map_sequence=12,
                ),
            )
        status = await self.recorder.stop()
        path = self.directory / f"{status.session_id}.jsonl"
        report = await SessionReplay(path).run()
        self.assertEqual(report["events"][MAPPING_SESSION.name], 3)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(
            [row["payload"]["state"] for row in rows[1:-1]],
            ["active", "paused", "idle"],
        )

    async def test_replay_rejects_missing_footer_unknown_version_and_changed_sequence(
        self,
    ) -> None:
        path = await self.record_session()
        original = path.read_text().splitlines()
        for mutation, expected in (
            (original[:-1], "missing footer"),
            (
                [original[0].replace('"format_version":1', '"format_version":99')]
                + original[1:],
                "format_version",
            ),
            (
                original[:1]
                + [original[1].replace('"sequence":0', '"sequence":7')]
                + original[2:],
                "discontinuous",
            ),
        ):
            with self.subTest(expected=expected):
                broken = self.directory / "broken.jsonl"
                broken.write_text("\n".join(mutation) + "\n")
                with self.assertRaisesRegex(ValueError, expected):
                    await SessionReplay(broken).run()

    async def test_step_advances_recorded_clock_and_close_releases_file(self) -> None:
        replay = SessionReplay(await self.record_session())
        try:
            event = replay.step()
            self.assertIsNotNone(event)
            assert event is not None
            self.assertEqual(replay.clock.monotonic_ns(), event.received_monotonic_ns)
            self.assertEqual(sum(replay.counts.values()), 1)
        finally:
            replay.close()
        clock = ReplayClock()
        clock.advance_to(10)
        with self.assertRaisesRegex(ValueError, "backwards"):
            clock.advance_to(9)

    async def test_lidar_no_return_infinity_round_trips_through_json_null(self) -> None:
        await self.recorder.start({}, {})
        self.bus.publish(
            LIDAR_SCAN,
            LaserScan(
                header=MessageHeader(
                    sequence=1, frame_id="lidar", timestamp_monotonic_ns=100
                ),
                angle_min_rad=0,
                angle_max_rad=1,
                angle_increment_rad=1,
                range_min_m=0.1,
                range_max_m=10,
                ranges_m=(1.5, math.inf),
            ),
        )
        status = await self.recorder.stop()
        path = self.directory / f"{status.session_id}.jsonl"
        self.assertIn('"ranges_m":[1.5,null]', path.read_text())
        result = await SessionReplay(path).run()
        self.assertEqual(result["events"][LIDAR_SCAN.name], 1)
