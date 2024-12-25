import asyncio
import json
import os
from typing import TYPE_CHECKING, Any, Dict

from app.config.paths import DEFAULT_USER_SETTINGS, PX_SETTINGS_FILE
from app.util.file_util import load_json_file
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.services.car_control.calibration_service import CalibrationService
    from app.services.connection_service import ConnectionService
    from app.services.distance_service import DistanceService


class CarService(metaclass=SingletonMeta):
    def __init__(
        self,
        px: "PicarxAdapter",
        calibration_service: "CalibrationService",
        connection_manager: "ConnectionService",
        distance_service: "DistanceService",
    ):
        self.logger = Logger(name=__name__)
        self.px = px
        self.connection_manager = connection_manager
        self.calibration = calibration_service
        self.user_settings_file = PX_SETTINGS_FILE
        self.settings_file = (
            self.user_settings_file
            if os.path.exists(self.user_settings_file)
            else DEFAULT_USER_SETTINGS
        )
        self.settings: Dict[str, Any] = load_json_file(self.settings_file)
        self.robot_settings: Dict[str, Any] = self.settings.get("robot", {})
        self.distance_interval = self.robot_settings.get(
            "auto_measure_distance_delay_ms", 1000
        )
        self.auto_measure_distance_mode = self.robot_settings.get(
            "auto_measure_distance_mode", False
        )
        self.avoid_obstacles_mode = False
        self.max_speed = self.robot_settings.get("max_speed", 80)
        self.distance_service = distance_service
        self.px.set_cam_tilt_angle(0)
        self.px.set_cam_pan_angle(0)
        self.px.set_dir_servo_angle(0)

    async def broadcast(self):
        await self.connection_manager.broadcast_json(self.broadcast_payload)

    @property
    def current_state(self):
        """
        Returns key metrics of the current state as a dictionary.

        The returned dictionary contains:
        - "speed": Current speed.
        - "maxSpeed": The maximum allowed speed.
        - "direction": Current travel direction.
        - "servoAngle": Current servo direction angle.
        - "camPan": Current camera pan angle.
        - "camTilt": Current camera tilt angle.
        - "avoidObstacles": Whether avoid obstacles mode is on.
        - "distance": The measured distance in centimeters.
        - "autoMeasureDistanceMode": Whether the auto measure distance mode is on.
        """

        px_state = self.px.state
        return {
            "speed": px_state["speed"],
            "direction": px_state["direction"],
            "servoAngle": px_state["steering_servo_angle"],
            "camPan": px_state["cam_pan_angle"],
            "camTilt": px_state["cam_tilt_angle"],
            "maxSpeed": self.max_speed,
            "avoidObstacles": self.avoid_obstacles_mode,
            "distance": self.distance_service.distance,
            "autoMeasureDistanceMode": self.auto_measure_distance_mode,
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
            "resetCalibration": self.calibration.reset_calibration,
            "saveCalibration": self.calibration.save_calibration,
        }

        actions_map = {
            "move": self.handle_move,
            "setServoDirAngle": self.handle_set_servo_dir_angle,
            "stop": self.handle_stop,
            "setCamTiltAngle": self.handle_set_cam_tilt_angle,
            "setCamPanAngle": self.handle_set_cam_pan_angle,
            "avoidObstacles": self.handle_avoid_obstacles,
            "startAutoMeasureDistance": self.start_auto_measure_distance,
            "stopAutoMeasureDistance": self.stop_auto_measure_distance,
            "setMaxSpeed": self.handle_max_speed,
            "servoTest": self.servos_test,
        }

        calibrationData = None
        if action in calibration_actions_map:
            calibrationData = await calibration_actions_map[action]()
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

        elif action in actions_map:
            func = actions_map[action]
            await func(payload)
            await self.broadcast()

        else:
            error_msg = f"Unknown action: {action}"
            self.logger.warning(error_msg)
            await websocket.send_text(json.dumps({"error": error_msg, "type": action}))

    async def handle_stop(self, _: Any = None):
        await asyncio.to_thread(self.px.stop)

    async def handle_set_servo_dir_angle(self, payload: int):
        angle = payload or 0
        if self.px.state["steering_servo_angle"] != angle:
            await asyncio.to_thread(self.px.set_dir_servo_angle, angle)

    async def handle_set_cam_tilt_angle(self, payload: int):
        if self.px.state["cam_tilt_angle"] != payload:
            await asyncio.to_thread(self.px.set_cam_tilt_angle, payload)

    async def handle_set_cam_pan_angle(self, payload: int):
        angle = payload
        if self.px.state["cam_pan_angle"] != angle:
            await asyncio.to_thread(self.px.set_cam_pan_angle, angle)

    async def handle_avoid_obstacles(self, _=None):
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

    async def handle_max_speed(self, payload: int):
        self.max_speed = payload
        if self.px.state["speed"] > self.max_speed:
            await self.move(self.px.state["direction"], self.max_speed)

    async def handle_move(self, payload: Dict[str, Any]):
        """
        Handles move actions to control the car's direction and speed.

        Args:
            payload (dict): Payload containing direction and speed data.
        """
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
        if self.px.state["direction"] != direction or speed != self.px.state["speed"]:
            await self.move(direction, speed)

    async def move(self, direction: int, speed: int):
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
        self.settings: Dict[str, Any] = await asyncio.to_thread(
            load_json_file, self.settings_file
        )
        self.robot_settings: Dict[str, Any] = self.settings.get("robot", {})
        self.distance_interval = self.robot_settings.get(
            "auto_measure_distance_delay_ms", 1000
        )
        distance_secs = self.distance_interval / 1000
        self.distance_service.interval = distance_secs
        await self.distance_service.start_all()

    async def stop_auto_measure_distance(self, _: Any = None):
        await self.distance_service.stop_all()
        self.auto_measure_distance_mode = False

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
