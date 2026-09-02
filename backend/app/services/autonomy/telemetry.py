"""Bounded external telemetry projection for the native robot topic bus."""

import asyncio
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    cast,
)

from app.schemas.autonomy import (
    EncoderState,
    ImuData,
    LaserScan,
    LocalizationPose2D,
    Odometry2D,
    SafetyState,
    SimulationState,
)
from app.schemas.autonomy.telemetry import (
    LaserScanTelemetry,
    TelemetryChannel,
    TelemetryEnvelope,
    json_safe_ranges,
)
from app.services.autonomy.topic_bus import Topic, TopicBus, TopicSubscription
from app.services.autonomy.topics import (
    ENCODER_STATE,
    IMU_DATA,
    LIDAR_SCAN,
    LOCALIZATION_POSE,
    ODOMETRY,
    SAFETY_STATE,
    SIMULATION_STATE,
)


TelemetrySink = Callable[[Dict[str, Any]], Awaitable[None]]

TELEMETRY_TOPICS: Mapping[TelemetryChannel, Topic[Any]] = {
    "lidar": LIDAR_SCAN,
    "imu": IMU_DATA,
    "encoder": ENCODER_STATE,
    "odometry": ODOMETRY,
    "localization": LOCALIZATION_POSE,
    "safety": SAFETY_STATE,
    "simulation": SIMULATION_STATE,
}
DEFAULT_TELEMETRY_CHANNELS: Tuple[TelemetryChannel, ...] = tuple(
    TELEMETRY_TOPICS.keys()
)


def parse_telemetry_channels(value: str) -> Tuple[TelemetryChannel, ...]:
    """Parse a comma-separated channel list, preserving order and uniqueness."""

    channels: List[TelemetryChannel] = []
    for raw_channel in value.split(","):
        channel_name = raw_channel.strip().lower()
        if not channel_name:
            continue
        if channel_name not in TELEMETRY_TOPICS:
            expected = ", ".join(TELEMETRY_TOPICS)
            raise ValueError(
                f"unknown telemetry channel '{channel_name}'; expected {expected}"
            )
        channel = cast(TelemetryChannel, channel_name)
        if channel not in channels:
            channels.append(channel)
    if not channels:
        raise ValueError("at least one telemetry channel is required")
    return tuple(channels)


def make_telemetry_envelope(
    channel: TelemetryChannel,
    message: Any,
) -> TelemetryEnvelope:
    """Project an internal message into the stable, JSON-safe wire contract."""

    topic = TELEMETRY_TOPICS[channel]
    if channel == "lidar":
        if not isinstance(message, LaserScan):
            raise TypeError("lidar telemetry requires LaserScan")
        payload: Any = LaserScanTelemetry(
            header=message.header,
            angle_min_rad=message.angle_min_rad,
            angle_max_rad=message.angle_max_rad,
            angle_increment_rad=message.angle_increment_rad,
            range_min_m=message.range_min_m,
            range_max_m=message.range_max_m,
            ranges_m=json_safe_ranges(message.ranges_m),
            intensities=message.intensities,
        )
    else:
        expected_types = {
            "imu": ImuData,
            "encoder": EncoderState,
            "odometry": Odometry2D,
            "localization": LocalizationPose2D,
            "safety": SafetyState,
            "simulation": SimulationState,
        }
        expected_type = expected_types[channel]
        if not isinstance(message, expected_type):
            raise TypeError(f"{channel} telemetry requires {expected_type.__name__}")
        payload = message
    return TelemetryEnvelope(channel=channel, topic=topic.name, payload=payload)


class SensorTelemetryStreamer:
    """Sample latest topic values without ever blocking sensor publishers."""

    def __init__(
        self,
        bus: TopicBus,
        *,
        channels: Sequence[TelemetryChannel] = DEFAULT_TELEMETRY_CHANNELS,
        max_rate_hz: float = 10.0,
    ) -> None:
        if not 0 < max_rate_hz <= 30:
            raise ValueError("max_rate_hz must be in (0, 30]")
        if not channels:
            raise ValueError("at least one telemetry channel is required")
        self._bus = bus
        self._channels = tuple(dict.fromkeys(channels))
        self._period_s = 1.0 / max_rate_hz

    async def stream(self, sink: TelemetrySink) -> None:
        subscriptions = self._subscribe()
        try:
            while True:
                for channel, subscription in subscriptions:
                    message = self._take_latest(subscription)
                    if message is None:
                        continue
                    envelope = make_telemetry_envelope(channel, message)
                    await sink(envelope.model_dump(mode="json"))
                await asyncio.sleep(self._period_s)
        finally:
            for _, subscription in subscriptions:
                subscription.close()

    def _subscribe(
        self,
    ) -> Tuple[Tuple[TelemetryChannel, TopicSubscription[Any]], ...]:
        return tuple(
            (
                channel,
                self._bus.subscribe(
                    TELEMETRY_TOPICS[channel],
                    max_queue_size=1,
                    replay_latest=True,
                ),
            )
            for channel in self._channels
        )

    @staticmethod
    def _take_latest(subscription: TopicSubscription[Any]) -> Optional[Any]:
        latest = None
        while subscription.pending_messages:
            latest = subscription.get_nowait()
        return latest


__all__ = [
    "DEFAULT_TELEMETRY_CHANNELS",
    "SensorTelemetryStreamer",
    "TELEMETRY_TOPICS",
    "make_telemetry_envelope",
    "parse_telemetry_channels",
]
