"""Bounded topic recording with disk serialization on a worker thread."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, TextIO
import uuid

from pydantic import TypeAdapter

from app.schemas.autonomy.recording import (
    RecordingEvent,
    RecordingFooter,
    RecordingHeader,
    RecordingStatus,
)
from app.services.autonomy import topics
from app.services.autonomy.topic_bus import (
    PublishedMessage,
    Topic,
    TopicBus,
    TopicSubscription,
)


RECORDED_TOPICS: Dict[str, Topic[Any]] = {
    topic.name: topic
    for topic in (
        topics.ENCODER_STATE,
        topics.IMU_DATA,
        topics.LIDAR_SCAN,
        topics.STEERING_STATE,
        topics.ODOMETRY,
        topics.LOCALIZATION_POSE,
        topics.POSE_OBSERVATION,
        topics.MOTION_COMMANDED,
        topics.SAFETY_STATE,
        topics.SIMULATION_STATE,
        topics.LOCAL_MAP,
        topics.MISSION_STATUS,
        topics.NAVIGATION_PLAN,
        topics.MAPPING_SESSION,
    )
}
ADAPTERS: Dict[str, TypeAdapter[Any]] = {
    name: TypeAdapter(topic.message_type) for name, topic in RECORDED_TOPICS.items()
}
CONFIG_KEYS = (
    "schema_version",
    "localization_sensors",
    "ackermann_odometry",
    "pose_estimation",
    "motion_control",
    "lidar_safety",
    "local_mapping",
    "coherent_simulation",
    "steering_servo",
    "motors",
)


class AutonomyRecorder:
    """One opt-in session; queue overflow is reported and cannot stall driving."""

    def __init__(
        self,
        bus: TopicBus,
        directory: Path,
        *,
        queue_size: int = 2048,
        max_bytes: int = 256 * 1024 * 1024,
    ) -> None:
        if queue_size <= 0 or max_bytes <= 0:
            raise ValueError("recording limits must be positive")
        self._bus = bus
        self.directory = directory
        self._queue_size = queue_size
        self._max_bytes = max_bytes
        self._status = RecordingStatus()
        self._subscription: Optional[TopicSubscription[PublishedMessage]] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._stopping = False
        self._lock = asyncio.Lock()

    @property
    def status(self) -> RecordingStatus:
        return self._status.model_copy(
            update={
                "dropped_events": (
                    self._subscription.dropped_messages
                    if self._subscription
                    else self._status.dropped_events
                )
            }
        )

    async def start(
        self, config: Dict[str, Any], software: Dict[str, str]
    ) -> RecordingStatus:
        async with self._lock:
            if self._task is not None and not self._task.done():
                raise ValueError("a recording is already active")
            session_id = uuid.uuid4().hex
            header = RecordingHeader(
                session_id=session_id,
                created_utc=datetime.now(timezone.utc).isoformat(),
                config={key: config[key] for key in CONFIG_KEYS if key in config},
                software=software,
            )
            stream = await asyncio.to_thread(self._open, header)
            self._status = RecordingStatus(active=True, session_id=session_id)
            self._stopping = False
            self._subscription = self._bus.observe(
                max_queue_size=self._queue_size, replay_latest=True
            )
            self._task = asyncio.create_task(
                self._write(stream), name="autonomy-recorder"
            )
            return self.status

    def _open(self, header: RecordingHeader) -> TextIO:
        self.directory.mkdir(parents=True, exist_ok=True)
        stream = (self.directory / f"{header.session_id}.jsonl").open(
            "x", encoding="utf-8"
        )
        try:
            stream.write(header.model_dump_json() + "\n")
            stream.flush()
        except BaseException:
            stream.close()
            raise
        return stream

    async def stop(self) -> RecordingStatus:
        async with self._lock:
            self._stopping = True
            if self._task is not None:
                await asyncio.shield(self._task)
            return self.status

    async def _write(self, stream: TextIO) -> None:
        subscription = self._subscription
        assert subscription is not None
        error: Optional[str] = None
        dropped = 0
        try:
            while True:
                # Bound each flush so disk work never runs on the robot event loop.
                batch = []
                for _ in range(128):
                    try:
                        publication = subscription.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    if publication.topic in RECORDED_TOPICS:
                        batch.append(publication)
                if batch:
                    count, size = await asyncio.to_thread(
                        self._write_batch, stream, batch, self._status.events_written
                    )
                    self._status = self._status.model_copy(
                        update={
                            "events_written": self._status.events_written + count,
                            "bytes_written": size,
                        }
                    )
                if self._stopping or subscription.closed:
                    # Producers may keep publishing while stop drains, so detach once.
                    dropped = subscription.dropped_messages
                    remainder = []
                    while subscription.pending_messages and not subscription.closed:
                        publication = subscription.get_nowait()
                        if publication.topic in RECORDED_TOPICS:
                            remainder.append(publication)
                    subscription.close()
                    if remainder:
                        count, size = await asyncio.to_thread(
                            self._write_batch,
                            stream,
                            remainder,
                            self._status.events_written,
                        )
                        self._status = self._status.model_copy(
                            update={
                                "events_written": self._status.events_written + count,
                                "bytes_written": size,
                            }
                        )
                    break
                if not batch:
                    await asyncio.sleep(0.02)
        except Exception as exc:
            error = str(exc)
        finally:
            dropped = max(dropped, subscription.dropped_messages)
            subscription.close()
            footer = RecordingFooter(
                events_written=self._status.events_written,
                dropped_events=dropped,
                error=error,
            )
            try:
                await asyncio.to_thread(self._close, stream, footer)
            except Exception as exc:
                error = str(exc)
            self._status = self._status.model_copy(
                update={
                    "active": False,
                    "dropped_events": dropped,
                    "error": error,
                }
            )

    def _write_batch(
        self, stream: TextIO, batch: list[PublishedMessage], sequence: int
    ) -> tuple[int, int]:
        lines = []
        for publication in batch:
            payload = ADAPTERS[publication.topic].dump_python(
                publication.message, mode="json"
            )
            event = RecordingEvent(
                sequence=sequence + len(lines),
                received_monotonic_ns=publication.received_monotonic_ns,
                topic=publication.topic,
                payload=payload,
                snapshot=publication.snapshot,
            )
            lines.append(event.model_dump_json() + "\n")
        data = "".join(lines)
        if stream.tell() + len(data.encode("utf-8")) > self._max_bytes:
            raise ValueError("recording size limit reached; start a new session")
        stream.write(data)
        stream.flush()
        return len(lines), stream.tell()

    @staticmethod
    def _close(stream: TextIO, footer: RecordingFooter) -> None:
        try:
            stream.write(footer.model_dump_json() + "\n")
            stream.flush()
        finally:
            stream.close()
