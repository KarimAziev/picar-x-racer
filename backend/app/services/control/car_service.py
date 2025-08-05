import asyncio
import inspect
import json
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, Union

from app.core.px_logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.schemas.robot.config import HardwareConfig
from app.schemas.settings import Settings
from app.types.car import CarServiceState
from fastapi import WebSocket
from robot_hat.services.motor_service import MotorServiceDirection
from robot_hat.sunfounder.utils import reset_mcu_sync

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.managers.file_management.json_data_manager import JsonDataManager
    from app.services.connection_service import ConnectionService
    from app.services.control.calibration_service import CalibrationService
    from app.services.sensors.distance_service import DistanceService
    from app.services.sensors.led_service import LEDService
    from app.services.sensors.speed_estimator import SpeedEstimator


class CarService(metaclass=SingletonMeta):
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
    ):
        self.logger = Logger(name=__name__)
        self.px = px
        self.connection_manager = connection_manager
        self.calibration = calibration_service
        self.config_manager = config_manager
        self.led_service = led_service
        self.speed_estimator = speed_estimator

        self.app_settings_manager = app_settings_manager

        self.app_settings = Settings(**app_settings_manager.load_data())
        self.config = HardwareConfig(**app_settings_manager.load_data())

        self.app_settings_manager.on(
            self.app_settings_manager.UPDATE_EVENT, self.refresh_config
        )

        self.app_settings_manager.on(
            self.app_settings_manager.LOAD_EVENT, self.refresh_config
        )

        self.config_manager.on(
            self.config_manager.UPDATE_EVENT, self.refresh_hardware_config
        )
        self.config_manager.on(
            self.config_manager.LOAD_EVENT, self.refresh_hardware_config
        )

        self.auto_measure_distance_mode = False
        self.led_blinking = False
        self.avoid_obstacles_mode = False
        self.max_speed = self.app_settings.robot.max_speed
        self.distance_service = distance_service
        self.px.set_cam_tilt_angle(0)
        self.px.set_cam_pan_angle(0)
        self.px.set_dir_servo_angle(0)

    def refresh_hardware_config(self, data: Dict[str, Any]):
        self.config = HardwareConfig(**data)

    def refresh_config(self, data: Dict[str, Any]):
        self.app_settings = Settings(**data)

    async def broadcast(self):
        await self.connection_manager.broadcast_json(self.broadcast_payload)

    async def broadcast_calibration(self):
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
        return {
            "speed": self.px.state["speed"],
            "direction": self.px.state["direction"],
            "servoAngle": self.px.state["steering_servo_angle"],
            "camPan": self.px.state["cam_pan_angle"],
            "camTilt": self.px.state["cam_tilt_angle"],
            "maxSpeed": self.max_speed,
            "avoidObstacles": self.avoid_obstacles_mode,
            "distance": self.distance_service.distance,
            "autoMeasureDistanceMode": self.auto_measure_distance_mode,
            "ledBlinking": self.led_blinking,
        }

    @property
    def broadcast_payload(self):
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

    async def process_action(self, action: str, payload, websocket: WebSocket):
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
            "reverseRightMotor": self.calibration.reverse_right_motor,
            "reverseLeftMotor": self.calibration.reverse_left_motor,
            "resetCalibration": self.calibration.reset_calibration,
            "saveCalibration": self.calibration.save_calibration,
            "getCalibrationData": self.calibration.current_calibration_settings,
        }

        calibration_actions_with_payload = {
            "updateServoDirCali": self.calibration.update_servo_dir_angle,
            "updateCamPanCali": self.calibration.update_cam_pan_angle,
            "updateCamTiltCali": self.calibration.update_cam_tilt_angle,
            "updateLeftMotorCaliDir": self.calibration.update_left_motor_direction,
            "updateRightMotorCaliDir": self.calibration.update_right_motor_direction,
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
            self.logger.warning(error_msg)
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
        await asyncio.to_thread(self.px.stop)

    async def handle_set_servo_dir_angle(self, payload: float) -> None:
        await asyncio.to_thread(self.px.set_dir_servo_angle, payload)

    async def handle_set_cam_tilt_angle(self, payload: float) -> None:
        await asyncio.to_thread(self.px.set_cam_tilt_angle, payload)

    async def handle_set_cam_pan_angle(self, payload: float) -> None:
        await asyncio.to_thread(self.px.set_cam_pan_angle, payload)

    async def handle_avoid_obstacles(self, _=None) -> None:
        self.avoid_obstacles_mode = not self.avoid_obstacles_mode
        if self.avoid_obstacles_mode:
            await self.handle_stop()
            self.auto_measure_distance_mode = self.distance_service.running
            self.auto_measure_distance_mode_prev_interval = (
                self.distance_service.interval
            )
            self.distance_service.subscribe(self.avoid_obstacles_subscriber)
            self.distance_service.interval = 0.1
            await self.distance_service.start_all()
        else:
            self.distance_service.unsubscribe(self.avoid_obstacles_subscriber)
            await self.handle_stop()
            await self.distance_service.stop_all()
            if self.auto_measure_distance_mode_prev_interval:
                self.distance_service.interval = (
                    self.auto_measure_distance_mode_prev_interval
                )

            if self.auto_measure_distance_mode:
                await self.distance_service.start_all()

    async def servos_test(self, _=None) -> None:
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
        if self.px.state["speed"] > self.max_speed:
            await self.move(self.px.state["direction"], self.max_speed)

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
        if self.px.state["direction"] != direction or speed != self.px.state["speed"]:
            if speed == 0 or direction == 0:
                await self.handle_stop()
            else:
                await self.move(direction, speed)

    async def move(self, direction: MotorServiceDirection, speed: int) -> None:
        """
        Moves the car in the specified direction at the given speed.

        Args:
            direction (int): The direction to move the car (1 for forward, -1 for backward).
            speed (int): The speed at which to move the car.
        """
        if direction == 1:
            await asyncio.to_thread(self.px.forward, speed)
        elif direction == -1:
            await asyncio.to_thread(self.px.backward, speed)

    async def start_auto_measure_distance(self, _: Any = None):
        self.auto_measure_distance_mode = True
        self.app_settings_manager.load_data()

        self.distance_interval = (
            self.app_settings.robot.auto_measure_distance_delay_ms or 1000
        )

        distance_secs = self.distance_interval / 1000
        self.distance_service.interval = distance_secs
        await self.distance_service.start_all()

    async def stop_auto_measure_distance(self, _: Any = None):
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
        self.logger.info("distance %s speed=%s", distance, self.px.state["speed"])
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
        try:
            await asyncio.to_thread(self.px.cleanup)
        except Exception as e:
            self.logger.error("Failed to cleanup Picarx: %s", e)
