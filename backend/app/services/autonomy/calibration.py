"""Exclusive, timed calibration sessions using raw encoders and range readings."""

import asyncio
import hashlib
import json
import math
import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from app.schemas.autonomy.calibration import (
    CalibrationApply,
    CalibrationFinish,
    CalibrationHeartbeat,
    CalibrationKind,
    CalibrationStart,
    CalibrationStatus,
    CalibrationTrial,
)
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.schemas.robot.localization_sensors import (
    AS5048AEncoderConfig,
    AS5600LEncoderConfig,
)
from app.services.autonomy.messages import RobotMode
from app.services.autonomy.motion_control_service import MotionControlService
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import (
    ENCODER_STATE,
    IMU_DATA,
    LIDAR_SCAN,
    STEERING_POSITION,
)
from app.services.control.settings_service import SettingsService


class CalibrationError(ValueError):
    """A recoverable setup or measurement failure suitable for display."""


class CalibrationHardware(Protocol):
    @property
    def calibration_interrupted(self) -> bool: ...
    def acquire_calibration(self, owner: str) -> None: ...
    def calibration_command(
        self, owner: str, power: int, steering_degrees: float | None = None
    ) -> None: ...
    def release_calibration(self, owner: str) -> None: ...


@dataclass(frozen=True)
class Observation:
    time_s: float
    ticks: tuple[int, ...] | None
    encoder_sequence: int | None
    wall_m: float | None
    wall_time_s: float | None
    gyro: float | None
    imu_time_s: float | None
    sensor_angle: float | None


@dataclass
class Session:
    id: str
    request: CalibrationStart
    config: HardwareConfig
    fingerprint: str
    started: float
    heartbeat: float
    sequence: int = -1
    driving: bool = False
    drive_started: float | None = None
    released: float | None = None
    steering: float = 0
    observations: list[Observation] = field(default_factory=list)


def config_fingerprint(config: HardwareConfig) -> str:
    return hashlib.sha256(
        json.dumps(config.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()


def encoder_noise_limits(config: HardwareConfig) -> tuple[int, ...]:
    """Allow half a sensor-shaft degree of jitter, rounded up to whole counts.

    Native magnetic counts measure absolute angle and fluctuate at rest. GPIO
    edge counters and mock encoders have no angular measurement noise allowance.
    Limits follow the role order used by Observation, independent of config order.
    """
    return tuple(
        (
            math.ceil(16384 / 720)
            if isinstance(sensor, AS5048AEncoderConfig)
            else (
                math.ceil(4096 / 720) if isinstance(sensor, AS5600LEncoderConfig) else 0
            )
        )
        for role in ("left_wheel", "right_wheel", "rear_axle_average")
        for sensor in config.localization_sensors.encoder.sensors
        if sensor.role == role
    )


def encoder_traces(
    observations: list[Observation], limits: tuple[int, ...]
) -> list[tuple[int, ...]]:
    """Return each encoder's complete trial trace, rejecting gaps or role changes."""
    rows = []
    for obs in observations:
        if obs.ticks is None:
            raise CalibrationError(
                "Wheel readings stopped during the measurement. Repeat the trial."
            )
        if len(obs.ticks) != len(limits) or not obs.ticks:
            raise CalibrationError(
                "Wheel sensors changed during measurement. Repeat the trial."
            )
        rows.append(obs.ticks)
    return list(zip(*rows))


def fit_speed(points: list[tuple[float, float]]) -> float:
    """Fit distance versus monotonic observation time, independent of video FPS."""
    if len(points) < 3 or points[-1][0] - points[0][0] < 0.3:
        raise CalibrationError("Not enough fresh distance readings. Try a longer run.")
    times, distances = zip(*points)
    mean_t, mean_d = statistics.mean(times), statistics.mean(distances)
    denominator = sum((t - mean_t) ** 2 for t in times)
    if denominator <= 0:
        raise CalibrationError(
            "Sensor timestamps did not advance. Reconnect the sensor."
        )
    return sum((t - mean_t) * (d - mean_d) for t, d in points) / denominator


class GuidedCalibrationService:
    """Collect and review measurements; apply only explicitly selected trials."""

    def __init__(
        self,
        bus: TopicBus,
        hardware: CalibrationHardware,
        settings: SettingsService,
        motion: MotionControlService | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        autonomous_active: Callable[[], bool] = lambda: False,
    ) -> None:
        self.bus, self.hardware, self.settings, self.motion = (
            bus,
            hardware,
            settings,
            motion,
        )
        self.clock = clock
        self.autonomous_active = autonomous_active
        self.session: Session | None = None
        self.trials: list[CalibrationTrial] = []
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._power_ceiling = 20
        self._hardware_fault = False

    def observation(self, config: HardwareConfig) -> Observation:
        now = self.clock()
        encoder = self.bus.latest(ENCODER_STATE)
        imu = self.bus.latest(IMU_DATA)
        steering = self.bus.latest(STEERING_POSITION)
        scan = self.bus.latest(LIDAR_SCAN)
        ticks = None
        if encoder and 0 <= now - encoder.header.timestamp_monotonic_ns / 1e9 <= 0.25:
            ticks = tuple(
                reading.ticks
                for reading in (encoder.left, encoder.right, encoder.rear_axle_average)
                if reading is not None
            )
        gyro = None
        if imu and 0 <= now - imu.header.timestamp_monotonic_ns / 1e9 <= 0.25:
            gyro = imu.angular_velocity_z_radps
        angle = None
        if steering and 0 <= now - steering.header.timestamp_monotonic_ns / 1e9 <= 0.25:
            angle = steering.sensor_angle_deg
        wall = None
        if scan and 0 <= now - scan.header.timestamp_monotonic_ns / 1e9 <= 0.3:
            transform = config.localization_sensors.lidar.transform
            points = []
            for i, distance in enumerate(scan.ranges_m):
                angle_rad = (
                    scan.angle_min_rad
                    + i * scan.angle_increment_rad
                    + transform.yaw_rad
                )
                angle_rad = math.atan2(math.sin(angle_rad), math.cos(angle_rad))
                if (
                    abs(angle_rad) <= math.radians(18)
                    and scan.range_min_m < distance < scan.range_max_m
                    and math.isfinite(distance)
                ):
                    points.append(
                        (distance * math.sin(angle_rad), distance * math.cos(angle_rad))
                    )
            if len(points) >= 7:
                mean_y = statistics.mean(y for y, _ in points)
                mean_x = statistics.mean(x for _, x in points)
                spread = sum((y - mean_y) ** 2 for y, _ in points)
                if spread > 0.001:
                    slope = sum((y - mean_y) * (x - mean_x) for y, x in points) / spread
                    intercept = mean_x - slope * mean_y
                    residual = max(abs(x - intercept - slope * y) for y, x in points)
                    if abs(slope) < math.tan(math.radians(8)) and residual < 0.04:
                        wall = intercept + transform.x_m - slope * transform.y_m
        return Observation(
            now,
            ticks,
            encoder.header.sequence if ticks and encoder else None,
            wall,
            (
                scan.header.timestamp_monotonic_ns / 1e9
                if wall is not None and scan
                else None
            ),
            gyro,
            (
                imu.header.timestamp_monotonic_ns / 1e9
                if gyro is not None and imu
                else None
            ),
            angle,
        )

    def blockers(
        self,
        request: CalibrationStart,
        config: HardwareConfig,
        observation: Observation,
    ) -> list[str]:
        errors = []
        if self.autonomous_active():
            errors.append(
                "Turn off Avoid obstacles before starting guided calibration."
            )
        if self._hardware_fault:
            errors.append(
                "A motor stop failed. Disconnect motor power, check the hardware, and restart the robot application before another trial."
            )
        if config.coherent_simulation.enabled:
            errors.append(
                "Turn off Coherent simulation before measuring the real robot."
            )
        if request.kind in {"wheel_distance", "speed", "stopping"}:
            if not config.localization_sensors.encoder.enabled or not observation.ticks:
                errors.append(
                    "Enable Localization sensors > Drive encoders and wait for fresh wheel readings."
                )
            if any(
                sensor.driver == "mock"
                for sensor in config.localization_sensors.encoder.sensors
            ):
                errors.append(
                    "Select physical wheel encoders; mock readings cannot calibrate a real robot."
                )
        if request.kind in {"speed", "stopping"}:
            nav = config.navigation
            if nav.body_length_m is None or nav.rear_overhang_m is None:
                errors.append(
                    "Complete Body measurements before powered trials so the stopping boundary can include the robot."
                )
            else:
                overhang = (
                    nav.body_length_m - nav.rear_overhang_m
                    if request.direction == "forward"
                    else nav.rear_overhang_m
                )
                if request.stop_distance_m < overhang + 0.15:
                    errors.append(
                        f"Set the stop boundary to at least {(overhang + 0.15) * 100:.0f} cm from the rear axle, leaving extra room for coasting."
                    )
            if (
                not config.localization_sensors.lidar.enabled
                or observation.wall_m is None
            ):
                errors.append(
                    "Face a broad, flat wall with the wheels straight. Wait for a stable LiDAR distance."
                )
            if config.localization_sensors.lidar.driver == "mock":
                errors.append("Select a physical LiDAR for powered speed trials.")
            if not config.steering_servo.enabled or not any(
                motor.enabled for motor in config.motors
            ):
                errors.append(
                    "Configure and enable the steering servo and at least one motor."
                )
            if (
                abs(config.localization_sensors.lidar.transform.roll_rad) > 0.05
                or abs(config.localization_sensors.lidar.transform.pitch_rad) > 0.05
            ):
                errors.append(
                    "Mount LiDAR level before using the wall-distance speed guide."
                )
        if request.kind == "imu_bias":
            if not config.localization_sensors.imu.enabled or observation.gyro is None:
                errors.append(
                    "Enable Localization sensors > Inertial measurement unit and wait for fresh readings."
                )
            if config.localization_sensors.imu.driver == "mock":
                errors.append("Select a physical IMU for stationary calibration.")
        if request.kind in {"steering_center", "steering_range"}:
            if (
                not config.localization_sensors.steering.enabled
                or observation.sensor_angle is None
            ):
                errors.append(
                    "Enable Localization sensors > Steering position sensor and wait for fresh readings."
                )
            if config.localization_sensors.steering.driver == "mock":
                errors.append(
                    "Select a physical steering sensor before recording its angles."
                )
        return errors

    def status(
        self,
        kind: str = "wheel_distance",
        *,
        direction: str = "forward",
        stop_distance_m: float = 0.6,
    ) -> CalibrationStatus:
        config = self.settings.saved_settings
        session = self.session
        request = (
            session.request
            if session
            else CalibrationStart.model_validate(
                {
                    "kind": kind,
                    "direction": direction,
                    "stop_distance_m": stop_distance_m,
                }
            )
        )
        obs = self.observation(config)
        return CalibrationStatus(
            active=session is not None,
            max_power_percent=self._power_ceiling,
            session_id=session.id if session else None,
            kind=request.kind,
            driving=bool(session and session.driving),
            elapsed_s=self.clock() - session.started if session else 0,
            encoder_ticks=statistics.mean(obs.ticks) if obs.ticks else None,
            wall_distance_m=obs.wall_m,
            gyro_radps=obs.gyro,
            sensor_angle_deg=obs.sensor_angle,
            blockers=self.blockers(request, config, obs),
            trials=self.trials,
        )

    async def start(self, request: CalibrationStart) -> CalibrationStatus:
        async with self._lock:
            if self.session:
                raise CalibrationError(
                    "Another calibration is active. Finish or cancel it first."
                )
            if getattr(self.hardware, "servo_tuning_active", False) is True:
                raise CalibrationError(
                    "Stop servo tuning before starting guided motion calibration"
                )
            config = self.settings.saved_settings.model_copy(deep=True)
            obs = self.observation(config)
            errors = self.blockers(request, config, obs)
            if errors:
                raise CalibrationError(" ".join(errors))
            if not request.clear_path_confirmed:
                raise CalibrationError(
                    "Confirm the robot is on a level surface with a clear path before starting."
                )
            powered = request.kind in {"speed", "stopping"}
            max_power = min(
                (motor.max_speed for motor in config.motors if motor.enabled), default=0
            )
            if powered and request.power_percent > min(self._power_ceiling, max_power):
                raise CalibrationError(
                    f"Start at or below {min(self._power_ceiling, max_power)}% motor power. Complete a trial before increasing power by up to 10%."
                )
            if self.motion:
                if (
                    self.motion.mode not in {RobotMode.DISARMED, RobotMode.MANUAL}
                    or self.motion.autonomy_owner
                ):
                    raise CalibrationError(
                        "Stop autonomous driving and clear any emergency stop or fault before calibration."
                    )
                self.motion.calibration_active = True
                try:
                    await self.motion.set_mode(RobotMode.DISARMED)
                    await self.motion.stop()
                except Exception:
                    self.motion.calibration_active = False
                    raise
            identifier = uuid.uuid4().hex
            try:
                await asyncio.to_thread(self.hardware.acquire_calibration, identifier)
                if (
                    self.motion and self.motion.mode != RobotMode.DISARMED
                ) or self.hardware.calibration_interrupted:
                    await asyncio.to_thread(
                        self.hardware.release_calibration, identifier
                    )
                    raise CalibrationError(
                        "Another control stopped calibration during startup. Clear the stop before starting again."
                    )
            except Exception:
                if self.motion:
                    self.motion.calibration_active = False
                    self.motion.start()
                raise
            now = self.clock()
            self.session = Session(
                identifier,
                request,
                config,
                config_fingerprint(config),
                now,
                now,
                observations=[obs],
            )
            self._task = asyncio.create_task(
                self._run(identifier), name="guided-calibration-watchdog"
            )
            return self.status()

    def _require(self, identifier: str) -> Session:
        if not self.session or self.session.id != identifier:
            raise CalibrationError(
                "This calibration session has ended. Start a new trial."
            )
        return self.session

    async def heartbeat(
        self, identifier: str, message: CalibrationHeartbeat
    ) -> CalibrationStatus:
        async with self._lock:
            session = self._require(identifier)
            if message.sequence <= session.sequence:
                raise CalibrationError("Out-of-order calibration command ignored.")
            if self.clock() - session.heartbeat > (0.35 if session.driving else 2.0):
                await self._end(
                    "Connection or hold control was lost. Start a new trial."
                )
                raise CalibrationError("The session expired. Start a new trial.")
            session.sequence, session.heartbeat = message.sequence, self.clock()
            if self.hardware.calibration_interrupted or (
                self.motion and self.motion.mode != RobotMode.DISARMED
            ):
                await self._end(
                    "Calibration was stopped by another control. Start a new trial."
                )
                return self.status()
            if message.drive:
                if session.request.kind not in {"speed", "stopping"}:
                    raise CalibrationError("This measurement keeps the motors stopped.")
                if session.released is not None:
                    raise CalibrationError(
                        "One movement per trial. Finish this measurement before driving again."
                    )
                try:
                    self._check_drive(session)
                except CalibrationError as error:
                    await self._end(str(error))
                    raise
                if session.drive_started is None:
                    session.drive_started = self.clock()
                session.driving = True
            elif session.driving:
                session.driving = False
                session.released = self.clock()
            steering = (
                message.steering_degrees
                if session.request.kind in {"steering_center", "steering_range"}
                else 0.0
            )
            servo = session.config.steering_servo
            if not servo.min_angle <= steering <= servo.max_angle:
                raise CalibrationError(
                    "That steering position is outside the configured servo limits."
                )
            session.steering = steering
            power = (
                session.request.power_percent
                * (1 if session.request.direction == "forward" else -1)
                if session.driving
                else 0
            )
            try:
                await asyncio.to_thread(
                    self.hardware.calibration_command,
                    identifier,
                    power,
                    (
                        steering
                        if session.request.kind
                        in {"speed", "stopping", "steering_center", "steering_range"}
                        else None
                    ),
                )
            except Exception as error:
                await self._end(f"Hardware command failed: {error}")
                raise CalibrationError(
                    "The robot stopped because a hardware command failed."
                ) from error
            return self.status()

    def _check_drive(self, session: Session) -> None:
        obs = self.observation(session.config)
        errors = self.blockers(session.request, session.config, obs)
        if errors:
            raise CalibrationError(" ".join(errors))
        if (
            obs.gyro is not None
            and abs(obs.gyro - session.config.pose_estimation.imu_yaw_bias_radps) > 0.15
        ):
            raise CalibrationError(
                "The robot turned. Straighten the wheels and repeat the trial."
            )
        previous = next(
            (
                item
                for item in session.observations
                if item.wall_m is not None and 0.15 <= obs.time_s - item.time_s <= 0.4
            ),
            None,
        )
        if (
            previous
            and previous.wall_m is not None
            and obs.wall_m is not None
            and session.driving
        ):
            wrong_direction = (obs.wall_m - previous.wall_m) * (
                1 if session.request.direction == "forward" else -1
            )
            if wrong_direction > 0.02:
                raise CalibrationError(
                    "Movement is opposite to the requested direction. Check motor direction before another trial."
                )
        scan = self.bus.latest(LIDAR_SCAN)
        if scan is None:
            raise CalibrationError("LiDAR readings stopped.")
        front = session.request.direction == "forward"
        transform = session.config.localization_sensors.lidar.transform
        distances = []
        for i, distance in enumerate(scan.ranges_m):
            angle = (
                scan.angle_min_rad + i * scan.angle_increment_rad + transform.yaw_rad
            )
            if (
                not math.isfinite(distance)
                or not scan.range_min_m < distance < scan.range_max_m
            ):
                continue
            x, y = transform.x_m + distance * math.cos(
                angle
            ), transform.y_m + distance * math.sin(angle)
            heading = math.atan2(y, x if front else -x)
            if abs(heading) < math.radians(40):
                distances.append(math.hypot(x, y))
        if len(distances) < 5:
            raise CalibrationError(
                "LiDAR cannot see enough of the driving direction. Keep the path in sensor view."
            )
        if min(distances) <= session.request.stop_distance_m:
            raise CalibrationError(
                "The stopping boundary was reached. Move the robot back before another trial."
            )
        if (
            session.drive_started is not None
            and self.clock() - session.drive_started >= session.request.max_duration_s
        ):
            raise CalibrationError(
                "The trial time limit was reached. Use a shorter run or more clear space."
            )

    async def _run(self, identifier: str) -> None:
        try:
            while self.session and self.session.id == identifier:
                await asyncio.sleep(0.05)
                async with self._lock:
                    session = self.session
                    if session is None or session.id != identifier:
                        break
                    reason = None
                    if self.clock() - session.heartbeat > (
                        0.35 if session.driving else 2.0
                    ):
                        reason = "Connection or hold control was lost. The robot stopped; repeat this trial."
                    elif self.clock() - session.started > 120:
                        reason = (
                            "The measurement timed out. Start a new trial when ready."
                        )
                    elif self.hardware.calibration_interrupted or (
                        self.motion and self.motion.mode != RobotMode.DISARMED
                    ):
                        reason = "Calibration was stopped by another control."
                    elif (
                        config_fingerprint(self.settings.saved_settings)
                        != session.fingerprint
                    ):
                        reason = "Robot settings changed during calibration. Repeat the trial with the current settings."
                    if session.driving and reason is None:
                        try:
                            self._check_drive(session)
                        except CalibrationError as error:
                            reason = str(error)
                    if reason:
                        await self._end(reason)
                        break
                    obs = self.observation(session.config)
                    previous = session.observations[-1]
                    if (
                        previous.encoder_sequence is not None
                        and obs.encoder_sequence is not None
                        and obs.encoder_sequence < previous.encoder_sequence
                    ):
                        await self._end("Wheel sensor restarted. Repeat the trial.")
                        break
                    session.observations.append(obs)
        except asyncio.CancelledError:
            async with self._lock:
                if self.session and self.session.id == identifier:
                    await self._end("Calibration cancelled.")
            raise
        except Exception as error:
            async with self._lock:
                if self.session and self.session.id == identifier:
                    await self._end(f"Measurement stopped: {error}")

    async def _release(self, session: Session) -> None:
        self.session = None
        try:
            await asyncio.to_thread(self.hardware.release_calibration, session.id)
        except Exception as error:
            self._hardware_fault = True
            # Keep the hardware lease and arming gate latched after a failed stop.
            raise CalibrationError(
                "Motor stop could not be confirmed. Disconnect motor power and check the hardware before restarting."
            ) from error
        if self.motion:
            self.motion.calibration_active = False
            # Disarmed after setup; never resume the previous driving mode.
            self.motion.start()

    async def _end(self, reason: str) -> None:
        session = self.session
        if not session:
            return
        try:
            self.trials.append(self._trial(session, False, reason))
            self.trials = self.trials[-60:]
        finally:
            await self._release(session)

    def _trial(
        self, session: Session, accepted: bool, reason: str, **values: Any
    ) -> CalibrationTrial:
        return CalibrationTrial(
            id=session.id,
            kind=session.request.kind,
            accepted=accepted,
            reason=reason,
            direction=session.request.direction,
            power_percent=session.request.power_percent,
            duration_s=self.clock() - session.started,
            config_fingerprint=session.fingerprint,
            **values,
        )

    async def cancel(self, identifier: str) -> CalibrationStatus:
        async with self._lock:
            self._require(identifier)
            await self._end("Cancelled. No settings were changed.")
            return self.status()

    async def stop(self) -> None:
        async with self._lock:
            if self.session:
                await self._end(
                    "Robot application stopped. No calibration was applied."
                )
        task, self._task = self._task, None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def finish(
        self, identifier: str, request: CalibrationFinish
    ) -> CalibrationStatus:
        async with self._lock:
            session = self._require(identifier)
            if session.driving:
                raise CalibrationError(
                    "Release the driving button and wait for the robot to stop before finishing."
                )
            session.observations.append(self.observation(session.config))
            try:
                if self.hardware.calibration_interrupted:
                    raise CalibrationError(
                        "Calibration was interrupted. Repeat the trial."
                    )
                if session.fingerprint != config_fingerprint(
                    self.settings.saved_settings
                ):
                    raise CalibrationError(
                        "Settings changed during measurement. Repeat the trial."
                    )
                result = self.analyze(session, request)
                if session.request.kind in {"speed", "stopping"}:
                    self._power_ceiling = max(
                        self._power_ceiling,
                        min(100, session.request.power_percent + 10),
                    )
            except CalibrationError as error:
                result = self._trial(session, False, str(error))
                if (
                    str(error).startswith("No measurable")
                    and session.request.kind == "speed"
                ):
                    self._power_ceiling = max(
                        self._power_ceiling,
                        min(100, session.request.power_percent + 10),
                    )
            finally:
                await self._release(session)
            self.trials.append(result)
            self.trials = self.trials[-60:]
            return self.status()

    def analyze(self, session: Session, request: CalibrationFinish) -> CalibrationTrial:
        observations = session.observations
        kind = session.request.kind
        if kind == "wheel_distance":
            if request.measured_distance_m is None:
                raise CalibrationError(
                    "Enter the distance between your floor marks in centimetres."
                )
            limits = encoder_noise_limits(session.config)
            traces = encoder_traces(observations, limits)
            deltas = [trace[-1] - trace[0] for trace in traces]
            if not deltas or any(
                delta < max(20, 10 * limit) for delta, limit in zip(deltas, limits)
            ):
                raise CalibrationError(
                    "Too little forward wheel movement. Push forward with wheels rolling, or check encoder direction."
                )
            if max(deltas) / min(deltas) > 1.1:
                raise CalibrationError(
                    "Left and right wheels disagree by more than 10%. Keep the wheels straight and check for slipping."
                )
            for trace, limit in zip(traces, limits):
                peak = trace[0]
                for ticks in trace:
                    peak = max(peak, ticks)
                    if peak - ticks > limit:
                        raise CalibrationError(
                            "The wheels reversed during measurement. Repeat in one forward direction."
                        )
            return self._trial(
                session,
                True,
                "Wheel distance recorded. Repeat to check consistency.",
                distance_m=request.measured_distance_m,
                distance_per_tick_m=request.measured_distance_m
                / statistics.mean(deltas),
            )
        if kind == "imu_bias":
            unique = {
                obs.imu_time_s: obs.gyro
                for obs in observations
                if obs.imu_time_s is not None and obs.gyro is not None
            }
            if len(unique) < 50 or max(unique, default=0) - min(unique, default=0) < 3:
                raise CalibrationError(
                    "Keep the robot still for at least 3 seconds with fresh IMU readings."
                )
            values = list(unique.values())
            if (
                statistics.pstdev(values) > 0.01
                or max(values) - min(values) > 0.06
                or abs(statistics.mean(values)) > 0.5
            ):
                raise CalibrationError(
                    "The robot moved or the IMU readings were unstable. Leave it still and repeat."
                )
            if session.config.localization_sensors.encoder.enabled:
                limits = encoder_noise_limits(session.config)
                traces = encoder_traces(observations, limits)
                if any(
                    max(trace) - min(trace) > limit
                    for trace, limit in zip(traces, limits)
                ):
                    raise CalibrationError(
                        "The wheels moved. Keep the robot still and repeat."
                    )
            return self._trial(
                session,
                True,
                "Stationary rotation-sensor offset measured.",
                gyro_bias_radps=statistics.mean(values),
            )
        if kind in {"steering_center", "steering_range"}:
            angles = [
                obs.sensor_angle
                for obs in observations[-10:]
                if obs.sensor_angle is not None
            ]
            if len(angles) < 5:
                raise CalibrationError(
                    "Wait for stable steering-sensor readings before recording."
                )
            center = (
                math.degrees(
                    math.atan2(
                        statistics.mean(math.sin(math.radians(a)) for a in angles),
                        statistics.mean(math.cos(math.radians(a)) for a in angles),
                    )
                )
                % 360
            )
            if max(abs((a - center + 180) % 360 - 180) for a in angles) > 1:
                raise CalibrationError(
                    "The steering is still moving. Hold it steady and record again."
                )
            if kind == "steering_range" and request.measured_wheel_angle_deg is None:
                raise CalibrationError(
                    "Enter the measured wheel angle using a protractor. Positive turns right; negative turns left."
                )
            return self._trial(
                session,
                True,
                "Steering position recorded for review.",
                sensor_angle_deg=center,
                steering_degrees=(
                    session.steering
                    if kind == "steering_center"
                    else request.measured_wheel_angle_deg
                ),
            )
        if session.drive_started is None or session.released is None:
            raise CalibrationError(
                "Hold the drive button for a trial, then release it before finishing."
            )
        if self.clock() - session.released < 0.7:
            raise CalibrationError(
                "Wait at least one second after releasing the drive button."
            )
        points = sorted(
            {
                obs.wall_time_s: obs.wall_m
                for obs in observations
                if obs.wall_time_s is not None and obs.wall_m is not None
            }.items()
        )
        # Use sensor timestamps, exclude initial acceleration and the stop phase.
        moving = [
            (t, d)
            for t, d in points
            if session.drive_started + 0.5 <= t <= session.released
        ]
        direction = -1 if session.request.direction == "forward" else 1
        windows = []
        for i in range(len(moving)):
            window = [(t, d) for t, d in moving[i:] if t - moving[i][0] <= 0.6]
            if len(window) >= 4 and window[-1][0] - window[0][0] >= 0.4:
                windows.append(direction * fit_speed(window))
        if len(windows) < 3:
            raise CalibrationError(
                "Not enough steady movement. Try holding drive for at least 2 seconds with more clear space."
            )
        speed = statistics.median(windows)
        if speed < -0.01:
            raise CalibrationError(
                "The robot moved opposite to the requested direction. Check motor direction before another powered trial."
            )
        if speed < 0.02:
            raise CalibrationError(
                "No measurable movement at this power. Check the motor direction or increase power by 10% for the next trial."
            )
        if min(windows) < speed * 0.8 or max(windows) > speed * 1.2:
            raise CalibrationError(
                "Speed varied by more than 20%. Use a level floor and a longer steady run."
            )
        if any(
            obs.ticks is None or obs.wall_m is None
            for obs in observations
            if session.drive_started <= obs.time_s <= session.released
        ):
            raise CalibrationError(
                "Sensor readings were missing during movement. Repeat the trial."
            )
        wheel_samples = [
            obs.ticks
            for obs in observations
            if session.drive_started <= obs.time_s <= session.released and obs.ticks
        ]
        if len(wheel_samples) < 2 or len(wheel_samples[0]) != len(wheel_samples[-1]):
            raise CalibrationError(
                "Wheel readings did not cover the movement. Repeat the trial."
            )
        deltas = [
            (end - start) * (-direction)
            for start, end in zip(wheel_samples[0], wheel_samples[-1])
        ]
        if min(deltas) < 20 or max(deltas) / min(deltas) > 1.1:
            raise CalibrationError(
                "Wheel readings disagree with straight travel. Check encoder direction and wheel slip."
            )
        after = [(t, d) for t, d in points if t >= session.released + 0.3]
        if len(after) < 3 or abs(fit_speed(after)) > 0.02:
            raise CalibrationError(
                "The robot has not settled after stopping. Wait, then record another trial."
            )
        released = session.released
        stop_start = min(points, key=lambda point: abs(point[0] - released))[1]
        stopping = max(
            0.0, direction * (statistics.mean(d for _, d in after[-3:]) - stop_start)
        )
        return self._trial(
            session,
            True,
            "Steady speed measured. Repeat this power level before applying.",
            distance_m=abs(moving[-1][1] - moving[0][1]),
            mean_speed_mps=speed,
            minimum_speed_mps=min(windows),
            maximum_speed_mps=max(windows),
            stopping_distance_m=stopping,
        )

    def proposed_update(self, request: CalibrationApply) -> dict[str, Any]:
        if self.session:
            raise CalibrationError(
                "Finish the active measurement before applying calibration."
            )
        selected = [trial for trial in self.trials if trial.id in request.trial_ids]
        if len(selected) != len(request.trial_ids) or any(
            not trial.accepted for trial in selected
        ):
            raise CalibrationError(
                "Choose accepted trials from this application session."
            )
        config = self.settings.saved_settings
        if any(
            trial.config_fingerprint != config_fingerprint(config) for trial in selected
        ):
            raise CalibrationError(
                "Robot settings changed after these trials. Repeat the measurements before applying them."
            )
        kinds = {trial.kind for trial in selected}
        if len(kinds) != 1:
            raise CalibrationError("Apply one calibration task at a time.")
        kind = selected[0].kind
        if kind == "wheel_distance":
            scales = [
                trial.distance_per_tick_m
                for trial in selected
                if trial.distance_per_tick_m is not None
            ]
            if len(scales) < 2 or max(scales) / min(scales) > 1.05:
                raise CalibrationError(
                    "Select at least two distance trials that agree within 5%."
                )
            native = {
                16384 if isinstance(sensor, AS5048AEncoderConfig) else 4096
                for sensor in config.localization_sensors.encoder.sensors
                if isinstance(sensor, (AS5048AEncoderConfig, AS5600LEncoderConfig))
            }
            ticks = (
                next(iter(native))
                if len(native) == 1
                else config.ackermann_odometry.encoder_ticks_per_revolution
            )
            if ticks is None or len(native) > 1:
                raise CalibrationError(
                    "For this encoder, enter its counts per revolution under Ackermann odometry before calibrating distance."
                )
            radius = (
                statistics.median(scales)
                * ticks
                * config.ackermann_odometry.gear_ratio
                / (2 * math.pi)
            )
            return {
                "ackermann_odometry": {
                    "wheel_radius_m": radius,
                    "encoder_ticks_per_revolution": ticks,
                }
            }
        if kind == "imu_bias":
            values = [
                trial.gyro_bias_radps
                for trial in selected
                if trial.gyro_bias_radps is not None
            ]
            if len(values) < 2 or max(values) - min(values) > 0.01:
                raise CalibrationError(
                    "Select two stationary trials whose offsets agree within 0.01 rad/s."
                )
            return {"pose_estimation": {"imu_yaw_bias_radps": statistics.mean(values)}}
        if kind == "steering_center":
            if (
                len(selected) != 1
                or selected[0].sensor_angle_deg is None
                or selected[0].steering_degrees is None
            ):
                raise CalibrationError("Choose one straight-wheel measurement.")
            trial = selected[0]
            servo = config.steering_servo
            if servo.calibration_mode.value not in {"sum", "negative"}:
                raise CalibrationError(
                    "Choose Sum or Negative offset mode in Advanced settings > Steering servo before calibrating its centre."
                )
            assert trial.steering_degrees is not None
            command = (
                -trial.steering_degrees if servo.reverse else trial.steering_degrees
            )
            command = min(servo.max_angle, max(servo.min_angle, command))
            offset = (servo.calibration_offset or 0) + command * (
                1 if servo.calibration_mode.value == "sum" else -1
            )
            return {
                "steering_servo": {
                    **servo.model_dump(mode="json"),
                    "calibration_offset": offset,
                    "saved_calibration_offset": offset,
                },
                "localization_sensors": {
                    "steering": {
                        "driver": config.localization_sensors.steering.driver,
                        "center_angle_deg": trial.sensor_angle_deg,
                        "calibration_points": [],
                    }
                },
            }
        if kind == "steering_range":
            sensor = config.localization_sensors.steering
            points = []
            for trial in selected:
                if trial.sensor_angle_deg is None or trial.steering_degrees is None:
                    continue
                offset = (
                    trial.sensor_angle_deg - sensor.center_angle_deg + 180
                ) % 360 - 180
                points.append(
                    {
                        "sensor_offset_deg": offset,
                        "wheel_angle_rad": math.radians(trial.steering_degrees),
                    }
                )
            points.sort(key=lambda p: p["sensor_offset_deg"])
            if (
                len(points) < 3
                or not any(p["wheel_angle_rad"] < 0 for p in points)
                or not any(p["wheel_angle_rad"] > 0 for p in points)
                or not any(
                    abs(p["wheel_angle_rad"]) < math.radians(0.5)
                    and abs(p["sensor_offset_deg"]) < 1
                    for p in points
                )
            ):
                raise CalibrationError(
                    "Record straight, left, and right wheel angles before applying the steering table."
                )
            increasing = all(
                a["sensor_offset_deg"] < b["sensor_offset_deg"]
                and a["wheel_angle_rad"] < b["wheel_angle_rad"]
                for a, b in zip(points, points[1:])
            )
            decreasing = all(
                a["sensor_offset_deg"] < b["sensor_offset_deg"]
                and a["wheel_angle_rad"] > b["wheel_angle_rad"]
                for a, b in zip(points, points[1:])
            )
            if not increasing and not decreasing:
                raise CalibrationError(
                    "Steering measurements disagree. Record distinct positions in order from left through straight to right, using negative wheel angles for left."
                )
            if decreasing:
                for point in points:
                    point["sensor_offset_deg"] *= -1
                points.reverse()
            return {
                "localization_sensors": {
                    "steering": {
                        "driver": sensor.driver,
                        "calibration_points": points,
                        "invert_direction": decreasing,
                    }
                }
            }
        if kind == "stopping":
            if len(selected) < 4 or any(
                sum(t.direction == direction for t in selected) < 2
                for direction in ("forward", "reverse")
            ):
                raise CalibrationError(
                    "Select at least two stopping trials in each direction."
                )
            nav = config.navigation
            if nav.body_length_m is None or nav.rear_overhang_m is None:
                raise CalibrationError(
                    "Complete Body measurements first so the stopping distance includes the robot body."
                )
            overhang = max(nav.rear_overhang_m, nav.body_length_m - nav.rear_overhang_m)
            braking = max(trial.stopping_distance_m or 0 for trial in selected)
            speed = max(trial.mean_speed_mps or 0 for trial in selected)
            for direction in ("forward", "reverse"):
                limit = getattr(config.motion_control, f"max_{direction}_speed_mps")
                directional = [t for t in selected if t.direction == direction]
                if limit is None or any(
                    (t.mean_speed_mps or 0) < limit * 0.95 for t in directional
                ):
                    raise CalibrationError(
                        "Measure stopping at the highest calibrated speed in each direction before applying safety distances."
                    )
            stop = max(
                config.lidar_safety.stop_distance_m or 0,
                overhang + braking + speed * 0.35 + 0.1,
            )
            return {
                "lidar_safety": {
                    "stop_distance_m": stop,
                    "slow_distance_m": max(
                        config.lidar_safety.slow_distance_m or 0, stop + max(0.2, speed)
                    ),
                }
            }
        curves: dict[str, Any] = {}
        for direction in ("forward", "reverse"):
            samples = [t for t in selected if t.direction == direction]
            levels = sorted({t.power_percent for t in samples})
            if len(levels) < 2:
                raise CalibrationError(
                    "Select two or more power levels in each direction, with two trials per level."
                )
            curve = []
            for power in levels:
                speeds = [
                    t.mean_speed_mps
                    for t in samples
                    if t.power_percent == power and t.mean_speed_mps is not None
                ]
                if len(speeds) < 2 or max(speeds) / min(speeds) > 1.1:
                    raise CalibrationError(
                        f"Repeat {direction} at {power}%: two trials must agree within 10%."
                    )
                curve.append(
                    {"power_percent": power, "speed_mps": statistics.median(speeds)}
                )
            curves[f"{direction}_speed_curve"] = curve
            curves[f"max_{direction}_speed_mps"] = curve[-1]["speed_mps"]
        return {"motion_control": curves}

    async def apply(self, request: CalibrationApply) -> CalibrationStatus:
        async with self._lock:
            if getattr(self.hardware, "servo_tuning_active", False) is True:
                raise CalibrationError(
                    "Stop servo tuning before applying guided measurements"
                )
            update = self.proposed_update(request)
            step: CalibrationKind = next(
                trial.kind for trial in self.trials if trial.id in request.trial_ids
            )
            if self.motion:
                self.motion.calibration_active = True
            try:
                if self.motion:
                    await self.motion.set_mode(RobotMode.DISARMED)
                saved = await asyncio.to_thread(
                    self.settings.merge_if_current,
                    PartialHardwareConfig.model_validate(update),
                    self.settings.saved_settings.model_copy(deep=True),
                    calibration_step=step,
                )
                if self.motion and "motion_control" in update:
                    self.motion.calibration_restart_required = True
            finally:
                if self.motion:
                    self.motion.calibration_active = False
            result = self.status()
            result.saved_config = saved.model_dump(mode="json", exclude_unset=True)
            return result
