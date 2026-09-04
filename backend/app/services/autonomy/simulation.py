"""Deterministic Ackermann plant and coherent simulated sensor publication."""

import asyncio
import math
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from app.core.logger import Logger
from app.schemas.autonomy import (
    EncoderReading,
    EncoderState,
    ImuData,
    LaserScan,
    MessageHeader,
    SimulationState,
    SteeringState,
)
from app.services.autonomy.messages import ActuatorCommand, MotionSource
from app.services.autonomy.simulation_world import (
    SimulationWorld,
    WorldLidarRaycaster,
)
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import (
    ENCODER_STATE,
    IMU_DATA,
    LIDAR_SCAN,
    MOTION_COMMANDED,
    SIMULATION_STATE,
    STEERING_STATE,
)


_log = Logger(__name__)


@dataclass(frozen=True)
class AckermannSimulationConfig:
    """Geometry, timing, and ideal-sensor parameters for one simulated car."""

    wheelbase_m: float
    wheel_radius_m: float
    encoder_ticks_per_revolution: int
    gear_ratio: float = 1.0
    update_frequency_hz: float = 100.0
    command_timeout_seconds: float = 0.25
    gravity_mps2: float = 9.80665

    def __post_init__(self) -> None:
        for name, value in (
            ("wheelbase_m", self.wheelbase_m),
            ("wheel_radius_m", self.wheel_radius_m),
            ("gear_ratio", self.gear_ratio),
            ("update_frequency_hz", self.update_frequency_hz),
            ("command_timeout_seconds", self.command_timeout_seconds),
            ("gravity_mps2", self.gravity_mps2),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and greater than zero")
        if self.encoder_ticks_per_revolution <= 0:
            raise ValueError("encoder_ticks_per_revolution must be greater than zero")

    @property
    def update_period_seconds(self) -> float:
        return 1.0 / self.update_frequency_hz

    @property
    def command_timeout_ns(self) -> int:
        return int(self.command_timeout_seconds * 1_000_000_000)


@dataclass(frozen=True)
class AckermannPlantState:
    """Internal ground truth after one deterministic plant update."""

    x_m: float
    y_m: float
    yaw_rad: float
    linear_speed_mps: float
    steering_angle_rad: float
    yaw_rate_radps: float
    longitudinal_acceleration_mps2: float
    lateral_acceleration_mps2: float
    encoder_ticks: int
    collision: bool


@dataclass(frozen=True)
class SimulationSensorImperfections:
    """Seeded errors applied only to simulated sensor observations."""

    enabled: bool = False
    random_seed: int = 7
    encoder_scale_error_percent: float = 1.0
    encoder_noise_stddev_ticks: float = 0.35
    steering_bias_deg: float = 0.75
    steering_noise_stddev_deg: float = 0.15
    imu_yaw_rate_bias_radps: float = 0.01
    imu_yaw_rate_noise_stddev_radps: float = 0.003
    lidar_range_noise_stddev_m: float = 0.015
    lidar_dropout_probability: float = 0.01

    def __post_init__(self) -> None:
        if self.random_seed < 0:
            raise ValueError("random_seed must be non-negative")
        finite_values = (
            self.encoder_scale_error_percent,
            self.encoder_noise_stddev_ticks,
            self.steering_bias_deg,
            self.steering_noise_stddev_deg,
            self.imu_yaw_rate_bias_radps,
            self.imu_yaw_rate_noise_stddev_radps,
            self.lidar_range_noise_stddev_m,
            self.lidar_dropout_probability,
        )
        if not all(math.isfinite(value) for value in finite_values):
            raise ValueError("sensor imperfection values must be finite")
        if self.encoder_scale_error_percent <= -100:
            raise ValueError(
                "encoder scale error must preserve the direction of travel"
            )
        for name, value in (
            ("encoder_noise_stddev_ticks", self.encoder_noise_stddev_ticks),
            ("steering_noise_stddev_deg", self.steering_noise_stddev_deg),
            (
                "imu_yaw_rate_noise_stddev_radps",
                self.imu_yaw_rate_noise_stddev_radps,
            ),
            ("lidar_range_noise_stddev_m", self.lidar_range_noise_stddev_m),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if not 0 <= self.lidar_dropout_probability <= 1:
            raise ValueError("lidar_dropout_probability must be between zero and one")


class AckermannSimulationPlant:
    """Ideal no-slip bicycle-model plant driven in SI units."""

    def __init__(
        self,
        config: AckermannSimulationConfig,
        *,
        collision_checker: Optional[Callable[[float, float], bool]] = None,
    ) -> None:
        self.config = config
        self._collision_checker = collision_checker
        self.reset()

    @property
    def state(self) -> AckermannPlantState:
        return AckermannPlantState(
            x_m=self._x_m,
            y_m=self._y_m,
            yaw_rad=self._yaw_rad,
            linear_speed_mps=self._linear_speed_mps,
            steering_angle_rad=self._steering_angle_rad,
            yaw_rate_radps=self._yaw_rate_radps,
            longitudinal_acceleration_mps2=self._longitudinal_acceleration_mps2,
            lateral_acceleration_mps2=self._lateral_acceleration_mps2,
            encoder_ticks=int(round(self._encoder_ticks)),
            collision=self._collision,
        )

    def reset(
        self,
        *,
        x_m: float = 0.0,
        y_m: float = 0.0,
        yaw_rad: float = 0.0,
        encoder_ticks: int = 0,
    ) -> AckermannPlantState:
        for name, value in (("x_m", x_m), ("y_m", y_m), ("yaw_rad", yaw_rad)):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        self._x_m = x_m
        self._y_m = y_m
        self._yaw_rad = self._normalize_angle(yaw_rad)
        self._linear_speed_mps = 0.0
        self._steering_angle_rad = 0.0
        self._yaw_rate_radps = 0.0
        self._longitudinal_acceleration_mps2 = 0.0
        self._lateral_acceleration_mps2 = 0.0
        self._encoder_ticks = float(encoder_ticks)
        self._collision = False
        return self.state

    def advance(
        self,
        command: ActuatorCommand,
        *,
        dt_seconds: float,
    ) -> AckermannPlantState:
        """Advance exactly one fixed step using the final arbiter command."""

        if not math.isfinite(dt_seconds) or dt_seconds <= 0:
            raise ValueError("dt_seconds must be finite and greater than zero")

        speed = command.linear_speed_mps
        steering = command.steering_angle_rad
        previous_speed = self._linear_speed_mps
        # The application-wide steering convention is negative for left. Pose
        # coordinates retain the mathematical convention of positive yaw for a
        # counter-clockwise/left turn, hence the sign inversion in curvature.
        yaw_rate = -speed / self.config.wheelbase_m * math.tan(steering)
        distance_m = speed * dt_seconds
        delta_yaw = yaw_rate * dt_seconds
        midpoint_yaw = self._yaw_rad + delta_yaw / 2

        candidate_x = self._x_m + distance_m * math.cos(midpoint_yaw)
        candidate_y = self._y_m + distance_m * math.sin(midpoint_yaw)
        collision = bool(
            distance_m
            and self._collision_checker is not None
            and self._collision_checker(candidate_x, candidate_y)
        )
        if collision:
            speed = 0.0
            yaw_rate = 0.0
            distance_m = 0.0
            delta_yaw = 0.0
        else:
            self._x_m = candidate_x
            self._y_m = candidate_y
            self._yaw_rad = self._normalize_angle(self._yaw_rad + delta_yaw)
        self._linear_speed_mps = speed
        self._steering_angle_rad = steering
        self._yaw_rate_radps = yaw_rate
        self._longitudinal_acceleration_mps2 = (speed - previous_speed) / dt_seconds
        self._lateral_acceleration_mps2 = speed * yaw_rate
        self._collision = collision
        wheel_revolutions = distance_m / (2 * math.pi * self.config.wheel_radius_m)
        self._encoder_ticks += (
            wheel_revolutions
            * self.config.encoder_ticks_per_revolution
            * self.config.gear_ratio
        )
        return self.state

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi


class CoherentSimulationService:
    """Publish synchronized ideal sensors derived from one simulated plant."""

    def __init__(
        self,
        bus: TopicBus,
        plant: AckermannSimulationPlant,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        initial_x_m: float = 0.0,
        initial_y_m: float = 0.0,
        initial_yaw_rad: float = 0.0,
        world: Optional[SimulationWorld] = None,
        lidar_raycaster: Optional[WorldLidarRaycaster] = None,
        sensor_imperfections: SimulationSensorImperfections = (
            SimulationSensorImperfections()
        ),
    ) -> None:
        self._bus = bus
        self._plant = plant
        self._monotonic_ns = monotonic_ns
        self._initial_pose = (initial_x_m, initial_y_m, initial_yaw_rad)
        self._world = world
        self._lidar_raycaster = lidar_raycaster
        self._sensor_imperfections = sensor_imperfections
        plant.reset(
            x_m=initial_x_m,
            y_m=initial_y_m,
            yaw_rad=initial_yaw_rad,
        )
        self._task: Optional[asyncio.Task[None]] = None
        self._sequence = 0
        self._last_timestamp_ns: Optional[int] = None
        self._last_truth_encoder_ticks = plant.state.encoder_ticks
        self._measured_encoder_ticks = (
            float(plant.state.encoder_ticks),
            float(plant.state.encoder_ticks),
        )
        self._last_measured_encoder_ticks = (
            plant.state.encoder_ticks,
            plant.state.encoder_ticks,
        )
        self._last_lidar_timestamp_ns: Optional[int] = None
        self._lidar_sequence = 0
        self.latest: Optional[SimulationState] = None
        self.last_error: Optional[Exception] = None
        self.published_updates = 0
        self.lidar_published_updates = 0
        self._reset_random_streams()

    @property
    def config(self) -> AckermannSimulationConfig:
        return self._plant.config

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def world(self) -> Optional[SimulationWorld]:
        return self._world

    @property
    def initial_pose(self) -> Tuple[float, float, float]:
        return self._initial_pose

    @property
    def sensor_imperfections(self) -> SimulationSensorImperfections:
        return self._sensor_imperfections

    def start(self) -> None:
        if self.running:
            return
        self.last_error = None
        self._task = asyncio.create_task(
            self._run(),
            name="coherent-ackermann-simulation",
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)

    def reset(
        self,
        *,
        x_m: Optional[float] = None,
        y_m: Optional[float] = None,
        yaw_rad: Optional[float] = None,
    ) -> SimulationState:
        if self.running:
            raise RuntimeError("stop the simulation before resetting it")
        initial_x, initial_y, initial_yaw = self._initial_pose
        state = self._plant.reset(
            x_m=initial_x if x_m is None else x_m,
            y_m=initial_y if y_m is None else y_m,
            yaw_rad=initial_yaw if yaw_rad is None else yaw_rad,
        )
        self._sequence = 0
        self._last_timestamp_ns = None
        self._last_truth_encoder_ticks = state.encoder_ticks
        self._measured_encoder_ticks = (
            float(state.encoder_ticks),
            float(state.encoder_ticks),
        )
        self._last_measured_encoder_ticks = (
            state.encoder_ticks,
            state.encoder_ticks,
        )
        self._last_lidar_timestamp_ns = None
        self._lidar_sequence = 0
        self.latest = None
        self.last_error = None
        self.published_updates = 0
        self.lidar_published_updates = 0
        self._reset_random_streams()
        return self._simulation_message(
            state,
            timestamp_ns=self._monotonic_ns(),
            source_timestamp_ns=None,
            sequence=0,
        )

    def step_once(self, *, timestamp_ns: Optional[int] = None) -> SimulationState:
        """Advance and publish one deterministic synchronized sensor frame."""

        timestamp = timestamp_ns if timestamp_ns is not None else self._monotonic_ns()
        if timestamp < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if self._last_timestamp_ns is not None and timestamp <= self._last_timestamp_ns:
            raise ValueError("simulation timestamps must increase monotonically")

        command = self._fresh_command(timestamp)
        state = self._plant.advance(
            command,
            dt_seconds=self.config.update_period_seconds,
        )
        self._sequence += 1
        self._last_timestamp_ns = timestamp
        source_timestamp_ns = command.selected_monotonic_ns
        header = MessageHeader(
            sequence=self._sequence,
            frame_id="base_link",
            timestamp_monotonic_ns=timestamp,
            source_timestamp_ns=source_timestamp_ns,
        )
        steering = SteeringState(
            header=header,
            commanded_angle_rad=command.steering_angle_rad,
            measured_angle_rad=self._measured_steering_angle(state),
        )
        left_ticks, right_ticks = self._measured_encoder_state(state)
        left_delta = left_ticks - self._last_measured_encoder_ticks[0]
        right_delta = right_ticks - self._last_measured_encoder_ticks[1]
        encoder = EncoderState(
            header=header.model_copy(update={"frame_id": "rear_axle"}),
            left=EncoderReading(
                ticks=left_ticks,
                delta_ticks=left_delta,
            ),
            right=EncoderReading(
                ticks=right_ticks,
                delta_ticks=right_delta,
            ),
        )
        imu = ImuData(
            header=header,
            angular_velocity_z_radps=self._measured_yaw_rate(state),
            acceleration_x_mps2=state.longitudinal_acceleration_mps2,
            acceleration_y_mps2=state.lateral_acceleration_mps2,
            acceleration_z_mps2=self.config.gravity_mps2,
            yaw_rad=state.yaw_rad,
            source_frame_id="imu",
        )
        simulation = self._simulation_message(
            state,
            timestamp_ns=timestamp,
            source_timestamp_ns=source_timestamp_ns,
            sequence=self._sequence,
        )

        self._bus.publish(STEERING_STATE, steering)
        self._bus.publish(ENCODER_STATE, encoder)
        self._bus.publish(IMU_DATA, imu)
        self._publish_lidar_if_due(state, timestamp)
        self._bus.publish(SIMULATION_STATE, simulation)
        self._last_truth_encoder_ticks = state.encoder_ticks
        self._last_measured_encoder_ticks = (left_ticks, right_ticks)
        self.latest = simulation
        self.published_updates = self._sequence
        self.last_error = None
        return simulation

    def _publish_lidar_if_due(
        self,
        state: AckermannPlantState,
        timestamp_ns: int,
    ) -> None:
        raycaster = self._lidar_raycaster
        if raycaster is None:
            return
        if (
            self._last_lidar_timestamp_ns is not None
            and timestamp_ns - self._last_lidar_timestamp_ns
            < raycaster.config.scan_period_ns
        ):
            return
        self._lidar_sequence += 1
        scan = raycaster.scan(
            base_x_m=state.x_m,
            base_y_m=state.y_m,
            base_yaw_rad=state.yaw_rad,
            timestamp_ns=timestamp_ns,
            sequence=self._lidar_sequence,
        )
        scan = self._measured_lidar_scan(scan)
        self._bus.publish(LIDAR_SCAN, scan)
        self._last_lidar_timestamp_ns = timestamp_ns
        self.lidar_published_updates = self._lidar_sequence

    def _measured_encoder_state(
        self,
        state: AckermannPlantState,
    ) -> Tuple[int, int]:
        model = self._sensor_imperfections
        if not model.enabled:
            self._measured_encoder_ticks = (
                float(state.encoder_ticks),
                float(state.encoder_ticks),
            )
            return state.encoder_ticks, state.encoder_ticks

        truth_delta = state.encoder_ticks - self._last_truth_encoder_ticks
        scale = 1 + model.encoder_scale_error_percent / 100
        measured = list(self._measured_encoder_ticks)
        if truth_delta:
            for index, generator in enumerate(self._encoder_random):
                measured[index] += truth_delta * scale + generator.gauss(
                    0,
                    model.encoder_noise_stddev_ticks,
                )
        self._measured_encoder_ticks = (measured[0], measured[1])
        return round(measured[0]), round(measured[1])

    def _measured_steering_angle(self, state: AckermannPlantState) -> float:
        model = self._sensor_imperfections
        if not model.enabled:
            return state.steering_angle_rad
        return state.steering_angle_rad + math.radians(
            model.steering_bias_deg
            + self._steering_random.gauss(0, model.steering_noise_stddev_deg)
        )

    def _measured_yaw_rate(self, state: AckermannPlantState) -> float:
        model = self._sensor_imperfections
        if not model.enabled:
            return state.yaw_rate_radps
        return (
            state.yaw_rate_radps
            + model.imu_yaw_rate_bias_radps
            + self._imu_random.gauss(0, model.imu_yaw_rate_noise_stddev_radps)
        )

    def _measured_lidar_scan(self, scan: LaserScan) -> LaserScan:
        model = self._sensor_imperfections
        if not model.enabled:
            return scan
        ranges = []
        intensities = list(scan.intensities) if scan.intensities is not None else None
        for index, distance in enumerate(scan.ranges_m):
            if not math.isfinite(distance):
                ranges.append(distance)
                continue
            if self._lidar_random.random() < model.lidar_dropout_probability:
                ranges.append(math.inf)
                if intensities is not None:
                    intensities[index] = 0.0
                continue
            measured_distance = distance + self._lidar_random.gauss(
                0,
                model.lidar_range_noise_stddev_m,
            )
            if not scan.range_min_m <= measured_distance <= scan.range_max_m:
                ranges.append(math.inf)
                if intensities is not None:
                    intensities[index] = 0.0
            else:
                ranges.append(measured_distance)
        return scan.model_copy(
            update={
                "ranges_m": tuple(ranges),
                "intensities": (
                    tuple(intensities) if intensities is not None else None
                ),
            }
        )

    def _reset_random_streams(self) -> None:
        seed = self._sensor_imperfections.random_seed
        # Independent streams ensure that enabling or changing one sensor does
        # not silently alter another sensor's repeatable error sequence.
        self._encoder_random = (
            random.Random(seed ^ 0x45A1),
            random.Random(seed ^ 0x45A2),
        )
        self._steering_random = random.Random(seed ^ 0x57EE)
        self._imu_random = random.Random(seed ^ 0x1A4D)
        self._lidar_random = random.Random(seed ^ 0x11DA)

    def _fresh_command(self, timestamp_ns: int) -> ActuatorCommand:
        command = self._bus.latest(MOTION_COMMANDED)
        if command is not None:
            age_ns = timestamp_ns - command.selected_monotonic_ns
            if 0 <= age_ns <= self.config.command_timeout_ns:
                return command
        return ActuatorCommand(
            source=MotionSource.IDLE,
            linear_speed_mps=0.0,
            steering_angle_rad=self._plant.state.steering_angle_rad,
            selected_monotonic_ns=timestamp_ns,
            reason="simulation command watchdog stopped the vehicle",
        )

    @staticmethod
    def _simulation_message(
        state: AckermannPlantState,
        *,
        timestamp_ns: int,
        source_timestamp_ns: Optional[int],
        sequence: int,
    ) -> SimulationState:
        return SimulationState(
            header=MessageHeader(
                sequence=sequence,
                frame_id="world",
                timestamp_monotonic_ns=timestamp_ns,
                source_timestamp_ns=source_timestamp_ns,
            ),
            x_m=state.x_m,
            y_m=state.y_m,
            yaw_rad=state.yaw_rad,
            linear_speed_mps=state.linear_speed_mps,
            steering_angle_rad=state.steering_angle_rad,
            yaw_rate_radps=state.yaw_rate_radps,
            longitudinal_acceleration_mps2=(state.longitudinal_acceleration_mps2),
            lateral_acceleration_mps2=state.lateral_acceleration_mps2,
            encoder_ticks=state.encoder_ticks,
            collision=state.collision,
        )

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        next_update = loop.time()
        try:
            while True:
                self.step_once()
                next_update += self.config.update_period_seconds
                delay = next_update - loop.time()
                if delay < -self.config.update_period_seconds:
                    next_update = loop.time()
                    delay = 0.0
                await asyncio.sleep(max(0.0, delay))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.last_error = error
            _log.error("Coherent simulation stopped after an error: %s", error)


class CoherentSimulationSupervisor:
    """Keep one hot-reconfigurable simulation lifecycle handle in app state."""

    def __init__(self, service: Optional[CoherentSimulationService] = None) -> None:
        self._service = service
        self._started = False
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self._service is not None

    @property
    def running(self) -> bool:
        return self._service is not None and self._service.running

    @property
    def service(self) -> Optional[CoherentSimulationService]:
        return self._service

    async def start(self) -> None:
        async with self._lock:
            self._started = True
            if self._service is not None:
                self._service.start()

    async def stop(self) -> None:
        async with self._lock:
            self._started = False
            if self._service is not None:
                await self._service.stop()

    async def reconfigure(
        self,
        service: Optional[CoherentSimulationService],
    ) -> None:
        async with self._lock:
            if self._service is not None:
                await self._service.stop()
            self._service = service
            if self._started and self._service is not None:
                self._service.start()

    async def reconfigure_from(
        self,
        replacement: "CoherentSimulationSupervisor",
    ) -> None:
        await self.reconfigure(replacement._service)

    async def reset(self) -> SimulationState:
        async with self._lock:
            service = self._service
            if service is None:
                raise RuntimeError("coherent simulation is disabled")
            if service.running:
                await service.stop()
            state = service.reset()
            if self._started:
                service.start()
            return state


__all__ = [
    "AckermannPlantState",
    "AckermannSimulationConfig",
    "AckermannSimulationPlant",
    "CoherentSimulationService",
    "CoherentSimulationSupervisor",
    "SimulationSensorImperfections",
]
