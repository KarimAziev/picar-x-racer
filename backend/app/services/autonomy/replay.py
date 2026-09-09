"""Offline JSONL playback and pose-estimator evaluation on a private topic bus.

Run from backend: python -m app.services.autonomy.replay SESSION.jsonl
"""

import argparse
import asyncio
from collections import Counter
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from app.schemas.autonomy import (
    ImuData,
    LocalizationPose2D,
    Odometry2D,
    PoseObservation2D,
)
from app.schemas.autonomy.recording import (
    RecordingEvent,
    RecordingFooter,
    RecordingHeader,
)
from app.schemas.robot.pose_estimation import PoseEstimationConfig
from app.services.autonomy.clock import ReplayClock
from app.services.autonomy.pose_estimation import PoseEstimator, PoseEstimatorConfig
from app.services.autonomy.recording import ADAPTERS, RECORDED_TOPICS
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import LOCALIZATION_POSE, LIDAR_SCAN


class SessionReplay:
    """No live-bus injection or hardware dependencies; step time advances explicitly.

    Recorded outputs are inspected as observations. Only the pure pose estimator
    is recomputed, from recorded odometry, IMU and correction observations.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.clock = ReplayClock()
        self._bus = TopicBus()
        self.header: Optional[RecordingHeader] = None
        self.footer: Optional[RecordingFooter] = None
        self.counts: Counter[str] = Counter()
        self.recomputed_pose: Optional[LocalizationPose2D] = None
        self._imu: Optional[ImuData] = None
        self._observation: Optional[PoseObservation2D] = None
        self._estimator: Optional[PoseEstimator] = None
        self._events = self._read()
        self._finished = False

    def _read(self) -> Iterator[RecordingEvent]:
        with self.path.open(encoding="utf-8") as stream:
            self.header = RecordingHeader.model_validate_json(
                stream.readline(16 * 1024 * 1024)
            )
            settings = PoseEstimationConfig.model_validate(
                self.header.config.get("pose_estimation", {})
            )
            self._estimator = PoseEstimator(
                PoseEstimatorConfig(
                    imu_yaw_rate_weight=settings.imu_yaw_rate_weight,
                    max_imu_age_seconds=settings.max_imu_age_ms / 1000,
                    max_pose_observation_age_seconds=settings.max_pose_observation_age_ms
                    / 1000,
                    initial_position_stddev_m=settings.initial_position_stddev_m,
                    initial_heading_stddev_rad=settings.initial_heading_stddev_rad,
                    position_process_noise_m_per_meter=settings.position_process_noise_m_per_meter,
                    heading_process_noise_rad_per_second=settings.heading_process_noise_rad_per_second,
                    odometry_heading_noise_fraction=settings.odometry_heading_noise_fraction,
                    imu_yaw_rate_stddev_radps=settings.imu_yaw_rate_stddev_radps,
                )
            )
            expected_sequence = 0
            while line := stream.readline(16 * 1024 * 1024):
                if not line.endswith("\n"):
                    raise ValueError("truncated or oversized recording line")
                data = json.loads(line)
                if not isinstance(data, dict):
                    raise ValueError("recording lines must contain JSON objects")
                if data.get("kind") == "footer":
                    self.footer = RecordingFooter.model_validate(data)
                    if self.footer.events_written != expected_sequence:
                        raise ValueError("recording event count does not match footer")
                    if stream.read(1):
                        raise ValueError("unexpected data after recording footer")
                    return
                event = RecordingEvent.model_validate(data)
                if event.sequence != expected_sequence:
                    raise ValueError("recording event sequence is discontinuous")
                if event.topic not in RECORDED_TOPICS:
                    raise ValueError(f"unsupported recorded topic: {event.topic}")
                expected_sequence += 1
                yield event
            raise ValueError("recording is incomplete: missing footer")

    def step(self) -> Optional[RecordingEvent]:
        """Apply one event on an asyncio event loop; no wall-clock waiting."""
        if self._finished:
            return None
        try:
            event = next(self._events)
        except StopIteration:
            self._finished = True
            return None
        self._apply(event)
        return event

    def _apply(self, event: RecordingEvent) -> None:
        self.clock.advance_to(event.received_monotonic_ns)
        payload = event.payload
        if event.topic == LIDAR_SCAN.name:
            # LaserScan permits positive infinity for no return, but not NaN or
            # missing samples. JSON's null is its lossless wire representation.
            payload = {
                **payload,
                "ranges_m": [
                    math.inf if value is None else value
                    for value in payload.get("ranges_m", [])
                ],
            }
        message = ADAPTERS[event.topic].validate_python(payload)
        self._bus.publish(RECORDED_TOPICS[event.topic], message)
        self.counts[event.topic] += 1
        if isinstance(message, ImuData):
            self._imu = message
        elif isinstance(message, PoseObservation2D):
            self._observation = message
        elif isinstance(message, Odometry2D) and not isinstance(
            message, LocalizationPose2D
        ):
            observation = self._observation
            if observation is not None:
                if (
                    observation.header.timestamp_monotonic_ns
                    > message.header.timestamp_monotonic_ns
                ):
                    observation = None
                else:
                    self._observation = None
            assert self._estimator is not None
            self.recomputed_pose = self._estimator.update(
                message, imu=self._imu, observation=observation
            ).pose

    async def run(self, *, speed: float = 0.0) -> Dict[str, Any]:
        """Zero speed runs without delays; positive speed scales inter-event waits."""
        if not math.isfinite(speed) or speed < 0:
            raise ValueError("replay speed must be finite and non-negative")
        previous: Optional[int] = None
        try:
            while True:
                # Peek without consuming so scaled waiting precedes publication.
                event = next(self._events, None)
                if event is None:
                    self._finished = True
                    break
                if previous is not None and speed > 0:
                    await asyncio.sleep(
                        max(0, event.received_monotonic_ns - previous) / 1e9 / speed
                    )
                self._apply(event)
                previous = event.received_monotonic_ns
                if sum(self.counts.values()) % 128 == 0:
                    await asyncio.sleep(0)
            recorded = self._bus.latest(LOCALIZATION_POSE)
            return {
                "session_id": self.header.session_id if self.header else None,
                "events": dict(self.counts),
                "dropped_events": self.footer.dropped_events if self.footer else None,
                "recording_error": self.footer.error if self.footer else None,
                "recorded_final_pose": (
                    recorded.model_dump(mode="json") if recorded else None
                ),
                "recomputed_final_pose": (
                    self.recomputed_pose.model_dump(mode="json")
                    if self.recomputed_pose
                    else None
                ),
            }
        finally:
            self.close()

    def close(self) -> None:
        close = getattr(self._events, "close", None)
        if close is not None:
            close()
        self._bus.close()
        self._finished = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--speed", type=float, default=0.0)
    args = parser.parse_args()
    try:
        result = asyncio.run(SessionReplay(args.session).run(speed=args.speed))
    except (ValueError, OSError) as error:
        parser.exit(1, f"Replay failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
