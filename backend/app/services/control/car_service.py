import asyncio
import inspect
import json
import math
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, Union, cast

from app.core.px_logger import Logger
from app.exceptions.robot import RobotI2CBusError, RobotI2CTimeout, ServoNotFoundError
from app.schemas.robot.avoid_obstacles import AvoidState
from app.schemas.robot.config import HardwareConfig
from app.schemas.settings import Settings
from app.services.autonomy.actuation import DriveDirection
from app.services.autonomy.messages import MotionIntent, MotionSource, RobotMode
from app.types.car import CarServiceBroadcastPayload, CarServiceState
from fastapi import WebSocket
from robot_hat import constrain
from robot_hat.services.motor_service import MotorServiceDirection
from robot_hat.sunfounder.utils import reset_mcu_sync

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.managers.file_management.json_data_manager import JsonDataManager
    from app.services.connection_service import ConnectionService
    from app.services.autonomy.motion_control_service import MotionControlService
    from app.services.control.calibration_service import CalibrationService
    from app.services.sensors.distance_service import DistanceService
    from app.services.sensors.led_service import LEDService
    from app.services.sensors.speed_estimator import SpeedEstimator

_log = Logger(name=__name__)


class CarService:
    def __init__(
        self,
        px: "PicarxAdapter",
        calibration_service: "CalibrationService",
        connection_manager: "ConnectionService",
        distance_service: "DistanceService",
        app_settings_manager: "JsonDataManager",
        config_manager: "JsonDataManager",
        led_service: "LEDService",
        speed_estimator: "SpeedEstimator",
        motion_control_service: Union["MotionControlService", None] = None,
    ) -> None:
        self.px = px
        self.connection_manager = connection_manager
        self.calibration = calibration_service
        self.config_manager = config_manager
        self.led_service = led_service
        self.speed_estimator = speed_estimator
        self.motion_control_service = motion_control_service

        self.app_settings_manager = app_settings_manager

        self.config = HardwareConfig(**config_manager.load_data())

        self.app_settings = Settings(**app_settings_manager.load_data())

        self.config_manager.on(
            self.app_settings_manager.UPDATE_EVENT, self.refresh_config
        )

        self.config_manager.on(
            self.app_settings_manager.LOAD_EVENT, self.refresh_config
        )

        self.app_settings_manager.on(
            self.app_settings_manager.UPDATE_EVENT, self.refresh_settings
        )

        self.app_settings_manager.on(
            self.app_settings_manager.LOAD_EVENT, self.refresh_settings
        )

        self.auto_measure_distance_mode = False
        self.led_blinking = False
        self.avoid_obstacles_mode = False
        self.max_speed = self.app_settings.robot.max_speed
        self.distance_service = distance_service
        for name, fn in [
            ("tilt", self.px.set_cam_tilt_angle),
            ("pan", self.px.set_cam_pan_angle),
            ("steering", self.px.set_dir_servo_angle),
        ]:
            try:
                fn(0)
            except ServoNotFoundError:
                pass
            except (RobotI2CTimeout, RobotI2CBusError) as e:
                _log.error("Failed to set angle for %s: %s", name, e)
            except Exception:
                _log.error(
                    "Unexpected error while zeroing angle for servo %s",
                    name,
                    exc_info=True,
                )

        self._avoid_task: Union[asyncio.Task, None] = None
        self._avoid_state: Union[AvoidState, None] = None
        self._avoid_params = self.config.avoid_obstacles_params
        self._prefer_right: bool = True
        self._state_since: float = time.monotonic()
        self._ema_distance: Union[float, None] = None
        self._last_distance_ts: Union[float, None] = None
        self._last_cmd = {"dir": 0, "speed": 0, "steer": 0.0}
        self._prev_distance_interval: Union[float, None] = None
        self._last_broadcast: float = 0.0
        self._motion_sequences: Dict[MotionSource, int] = {}
        self._desired_steering_degrees = 0.0

    @property
    def motion_control_enabled(self) -> bool:
        return self.motion_control_service is not None

    def _current_drive_state(self) -> tuple[MotorServiceDirection, int, float]:
        """Return the authoritative applied drive state for control continuity."""

        motion_service = self.motion_control_service
        applied = motion_service.applied_command if motion_service else None
        if applied is None:
            return (
                cast(MotorServiceDirection, self.px.state["direction"]),
                int(self.px.state["speed"]),
                float(self.px.state["steering_servo_angle"]),
            )
        direction_by_drive_state = {
            DriveDirection.STOPPED: 0,
            DriveDirection.FORWARD: 1,
            DriveDirection.REVERSE: -1,
        }
        return (
            cast(MotorServiceDirection, direction_by_drive_state[applied.direction]),
            applied.speed,
            applied.steering_angle_deg,
        )

    async def start_motion_control(self) -> None:
        """Start the opt-in runtime disarmed and begin its watchdog."""

        if not self.motion_control_service:
            return
        await self.motion_control_service.set_mode(RobotMode.DISARMED)
        self.motion_control_service.start()

    def refresh_config(self, data: Dict[str, Any]) -> None:
        self.config = HardwareConfig(**data)
        self._avoid_params = self.config.avoid_obstacles_params

    def refresh_settings(self, data: Dict[str, Any]) -> None:
        self.app_settings = Settings(**data)

    async def broadcast(self) -> None:
        await self.connection_manager.broadcast_json(self.broadcast_payload)

    async def broadcast_calibration(self) -> None:
        await self.connection_manager.broadcast_json(
            {
                "type": "updateCalibration",
                "payload": self.calibration.current_calibration_settings(),
            }
        )

    @property
    def current_state(self) -> CarServiceState:
        """
        Returns key metrics of the current state as a dictionary.

        The returned dictionary contains:
        - "speed": Current speed from 0 to 100%.
        - "maxSpeed": The maximum allowed speed from 0 to 100%.
        - "direction": Current travel direction.
        - "servoAngle": Current steering servo direction angle.
        - "camPan": Current camera pan angle.
        - "camTilt": Current camera tilt angle.
        - "avoidObstacles": Whether avoid obstacles mode is on.
        - "distance": The measured distance in centimeters.
        - "autoMeasureDistanceMode": Whether the auto measure distance mode is on.
        """
        motion_service = self.motion_control_service
        motion_result = motion_service.last_result if motion_service else None
        direction, speed, steering_angle = self._current_drive_state()
        return {
            "speed": speed,
            "direction": direction,
            "servoAngle": steering_angle,
            "camPan": self.px.state["cam_pan_angle"],
            "camTilt": self.px.state["cam_tilt_angle"],
            "maxSpeed": self.max_speed,
            "avoidObstacles": self.avoid_obstacles_mode,
            "distance": self.distance_service.distance,
            "autoMeasureDistanceMode": self.auto_measure_distance_mode,
            "ledBlinking": self.led_blinking,
            "motionControlEnabled": motion_service is not None,
            "robotMode": motion_service.mode.value if motion_service else "legacy",
            "motionGeneration": (
                motion_service.mode_generation if motion_service else 0
            ),
            "motionReason": (
                motion_result.command.reason if motion_result is not None else None
            ),
            "motionSource": (
                motion_result.command.source.value
                if motion_result is not None
                else None
            ),
            "emergencyStop": (
                motion_service.mode == RobotMode.ESTOP if motion_service else False
            ),
            "motionFault": (
                str(motion_service.last_error)
                if motion_service and motion_service.last_error
                else None
            ),
        }

    @property
    def broadcast_payload(self) -> CarServiceBroadcastPayload:
        """
        Returns the dictionary used for notifying clients about the current state.

        The broadcast message includes:
        - type: The type of message, set to "update".
        - payload: The current state of the object.
        """
        return {
            "type": "update",
            "payload": self.current_state,
        }

    async def process_action(self, action: str, payload, websocket: WebSocket) -> None:
        """
        Processes specific actions received from WebSocket messages and performs the corresponding operations.

        Args:
            action (str): The action to be performed.
            payload: The payload data associated with the action.
            websocket (WebSocket): WebSocket connection instance.
        """
        calibration_actions_map = {
            "increaseCamPanCali": self.calibration.increase_cam_pan_angle,
            "decreaseCamPanCali": self.calibration.decrease_cam_pan_angle,
            "increaseCamTiltCali": self.calibration.increase_cam_tilt_angle,
            "decreaseCamTiltCali": self.calibration.decrease_cam_tilt_angle,
            "increaseServoDirCali": self.calibration.increase_servo_dir_angle,
            "decreaseServoDirCali": self.calibration.decrease_servo_dir_angle,
            "resetCalibration": self.calibration.reset_calibration,
            "saveCalibration": self.calibration.save_calibration,
            "getCalibrationData": self.calibration.current_calibration_settings,
        }

        calibration_actions_with_payload = {
            "updateServoDirCali": self.calibration.update_servo_dir_angle,
            "updateCamPanCali": self.calibration.update_cam_pan_angle,
            "updateCamTiltCali": self.calibration.update_cam_tilt_angle,
            "reverseMotor": self.calibration.reverse_motor,
            "updateMotorCaliDir": self.calibration.update_motor_direction,
        }

        actions_map = {
            "move": self.handle_move,
            "update": self.handle_update,
            "setServoDirAngle": self.handle_set_servo_dir_angle,
            "setCamTiltAngle": self.handle_set_cam_tilt_angle,
            "setCamPanAngle": self.handle_set_cam_pan_angle,
            "stop": self.handle_stop,
            "avoidObstacles": self.handle_avoid_obstacles,
            "startAutoMeasureDistance": self.start_auto_measure_distance,
            "stopAutoMeasureDistance": self.stop_auto_measure_distance,
            "setMaxSpeed": self.handle_max_speed,
            "servoTest": self.servos_test,
            "resetMCU": self.reset_mcu,
            "setLedPin": self.handle_set_led_pin,
            "setLedInterval": self.handle_set_led_interval,
            "startLED": self.start_led_blinking,
            "stopLED": self.stop_led_blinking,
            "emergencyStop": self.handle_emergency_stop,
            "clearEmergencyStop": self.handle_clear_emergency_stop,
            "clearMotionFault": self.handle_clear_motion_fault,
            "setRobotMode": self.handle_set_robot_mode,
        }

        if action in calibration_actions_map:
            handler = calibration_actions_map[action]
            if inspect.iscoroutinefunction(handler):
                calibrationData = await handler()
            else:
                calibrationData = await asyncio.to_thread(handler)

            if calibrationData:

                await self.connection_manager.broadcast_json(
                    {
                        "type": (
                            "saveCalibration"
                            if action == "saveCalibration"
                            else "updateCalibration"
                        ),
                        "payload": calibrationData,
                    }
                )

        elif action in calibration_actions_with_payload:
            func = calibration_actions_with_payload[action]
            try:
                if inspect.iscoroutinefunction(func):
                    await func(payload)
                else:
                    func(payload)
            except ValueError as e:
                await self.connection_manager.error(str(e))

            await self.broadcast_calibration()
        elif action in actions_map:
            func = actions_map[action]
            if inspect.iscoroutinefunction(func):
                await func(payload)
            else:
                func(payload)

            await self.broadcast()

        else:
            error_msg = f"Unknown action: {action}"
            _log.warning(error_msg)
            await websocket.send_text(json.dumps({"error": error_msg, "type": action}))

    async def handle_set_led_pin(self, payload: Union[int, str]) -> None:
        """
        Updates the LED pin using LEDService.

        Payload should be an integer or a string representing the pin identifier.
        """
        try:
            await self.led_service.update_pin(payload)
            await self.connection_manager.info(f"LED pin updated to {payload}")
        except Exception as e:
            await self.connection_manager.error(f"Failed to update LED pin: {e}")

    async def handle_set_led_interval(self, payload: float) -> None:
        """
        Updates the LED blink interval using LEDService.

        Payload should be a float representing the new interval in seconds.
        """
        try:
            await self.led_service.update_interval(payload)
            await self.connection_manager.info(f"LED interval updated to {payload}")
        except Exception as e:
            await self.connection_manager.error(f"Failed to update LED interval: {e}")

    async def start_led_blinking(self, _: Any = None) -> None:
        await self.led_service.start_all()
        self.led_blinking = True

    async def stop_led_blinking(self, _: Any = None) -> None:
        await self.led_service.stop_all()
        self.led_blinking = False

    async def reset_mcu(self, _: Any = None) -> None:
        try:
            await asyncio.to_thread(reset_mcu_sync)
            await self.connection_manager.info("MCU has been reset")
        except Exception as e:
            await self.connection_manager.error(f"Failed to reset MCU: {e}")

    async def handle_stop(self, _: Any = None) -> None:
        if self.motion_control_service:
            await self._submit_motion(0, 0, self._desired_steering_degrees)
            return
        await asyncio.to_thread(self.px.stop)

    async def handle_emergency_stop(self, payload: Any = None) -> None:
        reason = str(payload).strip() if payload is not None else "operator request"
        if self.motion_control_service:
            await self.motion_control_service.emergency_stop(reason)
        else:
            await asyncio.to_thread(self.px.stop)

    async def handle_clear_emergency_stop(self, _: Any = None) -> None:
        if not self.motion_control_service:
            await self.connection_manager.error(
                "Emergency-stop latching requires enabled motion control"
            )
            return
        await self.motion_control_service.clear_emergency_stop()

    async def handle_clear_motion_fault(self, _: Any = None) -> None:
        if not self.motion_control_service:
            await self.connection_manager.error("Motion control is not enabled")
            return
        await self.motion_control_service.clear_fault()

    async def handle_set_robot_mode(self, payload: str) -> None:
        if not self.motion_control_service:
            await self.connection_manager.error("Motion control is not enabled")
            return
        try:
            mode = RobotMode(payload)
        except ValueError as error:
            raise ValueError(f"Unknown robot mode: {payload}") from error
        if mode in {RobotMode.ESTOP, RobotMode.FAULT}:
            raise ValueError(
                "Use the dedicated emergency-stop or fault operations for safety modes"
            )
        await self.motion_control_service.set_mode(mode)

    async def handle_set_servo_dir_angle(self, payload: float) -> None:
        angle = payload or 0
        self._desired_steering_degrees = float(angle)
        if self.motion_control_service:
            direction, speed, _ = self._current_drive_state()
            await self._submit_motion(
                direction,
                speed,
                self._desired_steering_degrees,
            )
            return
        if self.px.state["steering_servo_angle"] != angle:
            await asyncio.to_thread(self.px.set_dir_servo_angle, angle)

    async def handle_set_cam_tilt_angle(self, payload: float) -> None:
        if self.px.state["cam_tilt_angle"] != payload:
            await asyncio.to_thread(self.px.set_cam_tilt_angle, payload)

    async def handle_set_cam_pan_angle(self, payload: float) -> None:
        angle = payload
        if self.px.state["cam_pan_angle"] != angle:
            await asyncio.to_thread(self.px.set_cam_pan_angle, angle)

    async def handle_avoid_obstacles(self, _=None) -> None:
        self.avoid_obstacles_mode = not self.avoid_obstacles_mode

        if self.avoid_obstacles_mode:
            if self.motion_control_service:
                await self.motion_control_service.set_mode(RobotMode.AUTONOMOUS)
            await self.handle_stop()

            self.auto_measure_distance_mode = self.distance_service.running
            self._prev_distance_interval = self.distance_service.interval

            self.distance_service.interval = max(0.05, self._avoid_params.loop_period_s)
            await self.distance_service.start_all()

            self._avoid_state = AvoidState.CRUISSE if False else AvoidState.CRUISE
            self._prefer_right = True
            self._state_since = time.monotonic()
            self._ema_distance = None
            self._last_distance_ts = None
            self._last_cmd = {"dir": 0, "speed": 0, "steer": 0.0}

            self._avoid_task = asyncio.create_task(self._avoid_loop())
        else:
            await self._stop_avoid_loop()

            await self.handle_stop()

            if self.motion_control_service:
                await self.motion_control_service.set_mode(RobotMode.MANUAL)

            await self.distance_service.stop_all()
            if self._prev_distance_interval is not None:
                self.distance_service.interval = self._prev_distance_interval
            if self.auto_measure_distance_mode:
                await self.distance_service.start_all()

    async def _stop_avoid_loop(self) -> None:
        if self._avoid_task:
            self._avoid_task.cancel()
            try:
                await self._avoid_task
            except asyncio.CancelledError:
                pass
            finally:
                self._avoid_task = None

    def _smooth_distance(self, d: Union[float, None]) -> Union[float, None]:
        now = time.monotonic()

        invalid = (
            d is None
            or not isinstance(d, (int, float))
            or not math.isfinite(d)
            or d < 0
        )
        if invalid:
            if self._last_distance_ts is None:
                self._last_distance_ts = now
            return self._ema_distance

        d_val: float = float(cast(float, d))

        d_val = min(d_val, self._avoid_params.max_range_cm)

        self._last_distance_ts = now

        if self._ema_distance is None:
            self._ema_distance = d_val
        else:
            a: float = float(self._avoid_params.ema_alpha)
            ema = self._ema_distance
            self._ema_distance = a * d_val + (1.0 - a) * ema
        return self._ema_distance

    def _is_stale(self) -> bool:
        if self._last_distance_ts is None:
            return True
        return (
            time.monotonic() - self._last_distance_ts
        ) > self._avoid_params.stale_timeout_s

    def _ramp(
        self, current: float, target: float, dt: float, accel: float, decel: float
    ) -> float:
        delta = target - current
        if delta > 0:
            max_step = accel * dt
            delta = min(delta, max_step)
        else:
            max_step = decel * dt
            delta = max(delta, -max_step)
        return current + delta

    def _transition(self, new_state: AvoidState) -> None:
        self._avoid_state = new_state
        self._state_since = time.monotonic()

    def _state_time(self) -> float:
        return time.monotonic() - self._state_since

    async def _apply_drive(
        self, direction: MotorServiceDirection, speed: int, steer: float
    ) -> None:

        if not self.px.steering_servo:
            raise ServoNotFoundError("Servo not found")

        steer = constrain(
            steer, self.px.steering_servo.min_angle, self.px.steering_servo.max_angle
        )
        speed = max(0, min(min(self.max_speed or 80, speed), 100))

        if self.motion_control_service:
            self._desired_steering_degrees = float(steer)
            await self._submit_motion(direction, speed, steer)
            self._last_cmd["steer"] = steer
            self._last_cmd["dir"] = direction if speed else 0
            self._last_cmd["speed"] = speed
            return

        if steer != self._last_cmd["steer"]:
            await self.handle_set_servo_dir_angle(steer)
            self._last_cmd["steer"] = steer

        if direction != self.px.state["direction"] or speed != self.px.state["speed"]:
            if direction == 0 or speed == 0:
                await self.handle_stop()
                self._last_cmd["dir"] = 0
                self._last_cmd["speed"] = 0
            else:
                await self.move(direction, speed)
                self._last_cmd["dir"] = direction
                self._last_cmd["speed"] = speed

    async def _avoid_loop(self) -> None:
        p = self._avoid_params
        last_time = time.monotonic()
        try:
            while (
                self.avoid_obstacles_mode
                and self.distance_service._process
                and self.distance_service._process.is_alive()
            ):
                loop_start = time.monotonic()
                dt = loop_start - last_time
                last_time = loop_start

                raw_d = self.distance_service.distance
                d = self._smooth_distance(raw_d)

                target_dir = 0
                target_speed = 0
                target_steer = 0.0

                stale = self._is_stale()
                if stale:
                    (
                        self._transition(AvoidState.WAIT)
                        if self._avoid_state != AvoidState.WAIT
                        else None
                    )
                    target_dir, target_speed, target_steer = 0, 0, 0.0
                else:
                    dval = d if d is not None else 0.0

                    if self._avoid_state == AvoidState.CRUISE:
                        target_steer = 0.0
                        if dval < p.stop:
                            self._transition(AvoidState.REVERSE)
                        elif dval < p.danger:
                            self._transition(AvoidState.TURN)
                        else:
                            if dval <= p.caution:
                                target_speed = p.turn_speed
                            elif dval >= p.safe:
                                target_speed = p.forward_speed
                            else:
                                frac = (dval - p.caution) / (p.safe - p.caution)
                                target_speed = int(
                                    p.turn_speed
                                    + frac * (p.forward_speed - p.turn_speed)
                                )
                            target_dir = 1

                    elif self._avoid_state == AvoidState.TURN:
                        target_dir = 1
                        target_speed = p.turn_speed
                        target_steer = (
                            p.turn_angle if self._prefer_right else -p.turn_angle
                        )

                        if dval < p.stop:
                            self._transition(AvoidState.REVERSE)
                        elif dval >= p.safe and self._state_time() >= p.hold_cruise_s:
                            self._transition(AvoidState.CRUISE)

                    elif self._avoid_state == AvoidState.REVERSE:
                        target_dir = -1
                        target_speed = p.reverse_speed
                        target_steer = (
                            -p.reverse_angle if self._prefer_right else p.reverse_angle
                        )

                        if self._state_time() >= p.reverse_time_s:
                            self._transition(AvoidState.WAIT)
                            self._prefer_right = not self._prefer_right

                    elif self._avoid_state == AvoidState.WAIT:
                        target_dir = 0
                        target_speed = 0
                        target_steer = 0.0
                        if self._state_time() >= p.wait_time_s:
                            self._transition(AvoidState.TURN)
                    else:
                        self._transition(AvoidState.CRUISE)
                    _log.debug("target_steer=%s, dval=%s", target_steer, dval)

                current_dir, current_speed, _ = self._current_drive_state()
                desired_dir = target_dir
                ramp_target_speed = target_speed

                if desired_dir != current_dir and (current_speed > 0):
                    ramp_target_speed = 0

                ramped = self._ramp(
                    current=current_speed,
                    target=ramp_target_speed,
                    dt=dt if dt > 0 else p.loop_period_s,
                    accel=p.accel_rate,
                    decel=p.decel_rate,
                )

                if ramped == 0 and current_speed != 0 and desired_dir != current_dir:
                    await self.handle_stop()

                out_speed = int(round(ramped))
                out_dir = current_dir
                if out_speed == 0:
                    out_dir = 0
                elif current_speed == 0 and desired_dir != 0:
                    out_dir = desired_dir

                _log.debug("out_speed=%s, out_dir=%s", out_speed, out_dir)
                await self._apply_drive(out_dir, out_speed, target_steer)

                now = time.monotonic()
                if now - self._last_broadcast > 0.2:
                    self._last_broadcast = now
                    await self.broadcast()

                elapsed = time.monotonic() - loop_start
                sleep_time = max(0.0, p.loop_period_s - elapsed)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            await self.handle_stop()
            await self.broadcast()
        except ServoNotFoundError:
            await self.connection_manager.error("Servo is not found!")
            await self.handle_stop()
            await self.broadcast()
        except Exception:
            _log.error("Avoid loop crashed", exc_info=True)
            await self.handle_stop()
            await self.connection_manager.error("Avoid obstacles loop crashed")
            await self.broadcast()

    async def servos_test(self, _=None) -> None:
        if self.motion_control_service:
            for angle in [-30, 30, 0]:
                await self.handle_set_servo_dir_angle(angle)
                await self.broadcast()
                await asyncio.sleep(0.5)
            servos = [
                (self.px.set_cam_pan_angle, [-30, 30, 0]),
                (self.px.set_cam_tilt_angle, [-30, 30, 0]),
            ]
        else:
            servos = [
                (self.px.set_dir_servo_angle, [-30, 30, 0]),
                (self.px.set_cam_pan_angle, [-30, 30, 0]),
                (self.px.set_cam_tilt_angle, [-30, 30, 0]),
            ]
        for fn, args in servos:
            for arg in args:
                await asyncio.to_thread(fn, arg)
                await self.broadcast()
                await asyncio.sleep(0.5)

    async def handle_max_speed(self, payload: int) -> None:
        self.max_speed = payload
        direction, speed, _ = self._current_drive_state()
        if speed > self.max_speed:
            await self.move(direction, self.max_speed)

    async def handle_update(self, payload: Dict[str, Any]) -> None:
        current_state = self.current_state
        move_payload_changed = False
        handlers: Dict[str, Callable[[Any], Awaitable[None]]] = {
            "servoAngle": self.handle_set_servo_dir_angle,
            "camTilt": self.handle_set_cam_tilt_angle,
            "camPan": self.handle_set_cam_pan_angle,
        }

        for key, value in payload.items():
            if value is not None and current_state.get(key) != value:
                handler = handlers.get(key)
                if handler:
                    await handler(value)
                if key == "speed" or key == "direction" and not move_payload_changed:
                    move_payload_changed = True

        if move_payload_changed:
            await self.handle_move(
                {"speed": payload.get("speed"), "direction": payload.get("direction")}
            )

    async def handle_move(self, payload: Dict[str, Any]) -> None:
        """
        Handles move actions to control the car's direction and speed.

        Args:
            payload (dict): Payload containing direction and speed data.
        """
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
        if self.motion_control_service:
            if speed == 0 or direction == 0:
                await self.handle_stop()
            else:
                await self.move(direction, speed)
            return
        if self.px.state["direction"] != direction or speed != self.px.state["speed"]:
            if speed == 0 or direction == 0:
                await self.handle_stop()
            else:
                await self.move(direction, speed)

    async def move(self, direction: MotorServiceDirection, speed: int) -> None:
        """
        Moves the car in the specified direction at the given speed.

        Args:
            direction: The direction to move the car (1 for forward, -1 for backward).
            speed: The speed at which to move the car.
        """
        if self.motion_control_service:
            await self._submit_motion(
                direction,
                speed,
                self._desired_steering_degrees,
            )
        elif direction == 1:
            await asyncio.to_thread(self.px.forward, speed)
        elif direction == -1:
            await asyncio.to_thread(self.px.backward, speed)

    async def _submit_motion(
        self,
        direction: MotorServiceDirection,
        speed: int,
        steering_degrees: float,
    ) -> None:
        service = self.motion_control_service
        if service is None:
            raise RuntimeError("Motion control is not enabled")
        if direction not in (-1, 0, 1):
            raise ValueError("Motion direction must be -1, 0, or 1")

        source_by_mode = {
            RobotMode.MANUAL: MotionSource.MANUAL,
            RobotMode.AUTONOMOUS: MotionSource.AUTONOMY,
            RobotMode.CALIBRATION: MotionSource.CALIBRATION,
        }
        source = source_by_mode.get(service.mode)
        if source is None:
            await service.step()
            return

        enabled_motors = [motor for motor in self.config.motors if motor.enabled]
        if not enabled_motors:
            raise ValueError("Motion control requires an enabled motor")
        max_motor_command = min(100, *(motor.max_speed for motor in enabled_motors))
        configured_max_speed = int(self.max_speed or max_motor_command)
        command_speed = max(
            0,
            min(int(speed), max_motor_command, configured_max_speed),
        )
        motion_config = self.config.motion_control
        physical_max = (
            motion_config.max_forward_speed_mps
            if direction == 1
            else motion_config.max_reverse_speed_mps
        )
        if physical_max is None:
            raise ValueError("Motion control speed calibration is missing")
        linear_speed_mps = (
            command_speed / max_motor_command * physical_max if direction else 0.0
        )
        if direction == -1:
            linear_speed_mps = -linear_speed_mps

        now = time.monotonic_ns()
        sequence = self._motion_sequences.get(source, 0) + 1
        self._motion_sequences[source] = sequence
        result = service.submit(
            MotionIntent(
                command_id=f"{source.value}-{service.mode_generation}-{sequence}",
                source=source,
                sequence=sequence,
                mode_generation=service.mode_generation,
                linear_speed_mps=linear_speed_mps,
                steering_angle_rad=math.radians(steering_degrees),
                created_monotonic_ns=now,
                expires_monotonic_ns=(
                    now + motion_config.command_timeout_ms * 1_000_000
                ),
            )
        )
        if not result.accepted:
            reason = result.rejection_reason.value if result.rejection_reason else None
            raise ValueError(f"Motion command rejected: {reason or 'unknown reason'}")
        await service.step()

    async def start_auto_measure_distance(self, _: Any = None) -> None:
        self.auto_measure_distance_mode = True
        self.app_settings_manager.load_data()

        self.distance_interval = (
            self.app_settings.robot.auto_measure_distance_delay_ms or 1000
        )

        distance_secs = self.distance_interval / 1000
        self.distance_service.interval = distance_secs
        await self.distance_service.start_all()

    async def stop_auto_measure_distance(self, _: Any = None) -> None:
        await self.distance_service.stop_all()
        self.auto_measure_distance_mode = False
        self.speed_estimator.reset()
        await self.connection_manager.broadcast_json(
            {"type": "distance", "payload": {"distance": None, "speed": None}}
        )

    async def avoid_obstacles_subscriber(self, distance: float) -> None:
        POWER = 50
        SafeDistance = 40
        DangerDistance = 20
        _log.info("distance %s speed=%s", distance, self.px.state["speed"])
        if distance >= SafeDistance:
            await self.handle_set_servo_dir_angle(0)
            if self.px.state["speed"] != POWER or self.px.state["direction"] != 1:
                await self.move(1, POWER)
            await self.broadcast()
        elif distance >= DangerDistance:
            await self.handle_set_servo_dir_angle(30)
            if self.px.state["speed"] != POWER or self.px.state["direction"] != 1:
                await self.move(1, POWER)
            else:
                await asyncio.sleep(0.1)
            await self.broadcast()
        else:
            await self.handle_set_servo_dir_angle(-30)
            if self.px.state["speed"] != POWER or self.px.state["direction"] != -1:
                await self.move(-1, POWER)
            await self.broadcast()
            await asyncio.sleep(0.5)

    async def cleanup(self) -> None:
        async_handlers = [
            self._stop_avoid_loop,
            self.handle_stop,
            self.distance_service.stop_all,
        ]
        for fn in async_handlers:
            try:
                await fn()
            except Exception:
                pass

        if self.motion_control_service:
            try:
                await self.motion_control_service.stop()
            except Exception as e:
                _log.error("Failed to stop motion control service: %s", e)

        try:
            await asyncio.to_thread(self.px.cleanup)

        except Exception as e:
            _log.error("Failed to cleanup Picarx: %s", e)
