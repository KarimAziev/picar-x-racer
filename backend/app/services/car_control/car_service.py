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
    from app.services.car_control.avoid_obstacles_service import AvoidObstaclesService
    from app.services.car_control.calibration_service import CalibrationService
    from app.services.connection_service import ConnectionService


class CarService(metaclass=SingletonMeta):
    def __init__(
        self,
        px: "PicarxAdapter",
        avolid_obstacles_service: "AvoidObstaclesService",
        calibration_service: "CalibrationService",
        connection_manager: "ConnectionService",
    ):
        self.logger = Logger(name=__name__)
        self.px = px
        self.connection_manager = connection_manager
        self.avoid_obstacles_service = avolid_obstacles_service
        self.calibration = calibration_service
        self.user_settings_file = PX_SETTINGS_FILE
        self.settings_file = (
            self.user_settings_file
            if os.path.exists(self.user_settings_file)
            else DEFAULT_USER_SETTINGS
        )
        self.settings: Dict[str, Any] = load_json_file(self.settings_file)
        self.speed = 0
        self.max_speed = self.settings.get("max_speed", 80)
        self.direction = 0
        self.servo_dir_angle = 0
        self.cam_pan_angle = 0
        self.cam_tilt_angle = 0
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
        """
        return {
            "speed": self.speed,
            "maxSpeed": self.max_speed,
            "direction": self.direction,
            "servoAngle": self.servo_dir_angle,
            "camPan": self.cam_pan_angle,
            "camTilt": self.cam_tilt_angle,
            "avoidObstacles": self.avoid_obstacles_service.avoid_obstacles_mode,
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
            "resetCalibration": self.calibration.servos_reset,
            "saveCalibration": self.calibration.save_calibration,
            "servoTest": self.calibration.servos_test,
        }

        actions_map = {
            "move": self.handle_move,
            "setServoDirAngle": self.handle_set_servo_dir_angle,
            "stop": self.handle_stop,
            "setCamTiltAngle": self.handle_set_cam_tilt_angle,
            "setCamPanAngle": self.handle_set_cam_pan_angle,
            "avoidObstacles": self.handle_avoid_obstacles,
            "getDistance": self.handle_get_distance,
            "setMaxSpeed": self.handle_max_speed,
        }

        calibrationData = None
        if action in calibration_actions_map:
            calibrationData = calibration_actions_map[action]()
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
            await func(payload, websocket)
            await self.broadcast()

        else:
            error_msg = f"Unknown action: {action}"
            self.logger.warning(error_msg)
            await websocket.send_text(json.dumps({"error": error_msg, "type": action}))

    async def handle_stop(self, payload, _: WebSocket):
        await self.px.stop()
        self.direction = 0
        self.speed = 0

    async def handle_set_servo_dir_angle(self, payload, _: WebSocket):
        angle = payload or 0
        if self.servo_dir_angle != angle:
            await asyncio.to_thread(self.px.set_dir_servo_angle, angle)
            self.servo_dir_angle = angle

    async def handle_set_cam_tilt_angle(self, payload, _):
        angle = payload
        if self.cam_tilt_angle != angle:
            await asyncio.to_thread(self.px.set_cam_tilt_angle, angle)
            self.cam_tilt_angle = angle

    async def handle_set_cam_pan_angle(self, payload, _: WebSocket):
        angle = payload
        if self.cam_pan_angle != angle:
            await asyncio.to_thread(self.px.set_cam_pan_angle, angle)
            self.cam_pan_angle = angle

    async def handle_avoid_obstacles(self, _, websocket: WebSocket):
        response = await self.avoid_obstacles_service.toggle_avoid_obstacles_mode()
        if response is not None:
            self.speed = response.get("speed", self.speed)
            self.direction = response.get("direction", self.direction)
            self.servo_dir_angle = response.get("servoAngle", self.servo_dir_angle)
            self.cam_pan_angle = response.get("camPan", self.cam_pan_angle)
            self.cam_tilt_angle = response.get("camTilt", self.cam_tilt_angle)

            await self.connection_manager.broadcast_json(
                {
                    "payload": response,
                    "type": "update",
                }
            )

    async def handle_get_distance(self, _, websocket: WebSocket):
        await self.respond_with_distance("getDistance", websocket)

    async def handle_max_speed(self, payload: int, websocket: WebSocket):
        self.max_speed = payload
        if self.speed > self.max_speed:
            await self.move(self.direction, self.max_speed)

    async def handle_move(self, payload, _):
        """
        Handles move actions to control the car's direction and speed.

        Args:
            payload (dict): Payload containing direction and speed data.
        """
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
        if self.direction != direction or speed != self.speed:
            await self.move(direction, speed)

    async def respond_with_distance(self, action, websocket: WebSocket):
        """
        Responds with the distance measured by the car's ultrasonic sensor.

        Args:
            action (str): Action type for the distance request.
            websocket (WebSocket): WebSocket connection instance.
        """

        try:
            distance = await self.get_distance()
            response = {"payload": distance, "type": action}
            await self.connection_manager.broadcast_json(response)
        except Exception as e:
            error_response = {"type": action, "error": str(e)}
            await websocket.send_json(error_response)

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

        self.speed = speed

        self.direction = direction

    async def get_distance(self):
        """
        Measures and returns the distance using the car's ultrasonic sensor.

        Returns:
            float: The measured distance.

        Raises:
            ValueError: If an error occurs while measuring the distance.
        """

        errors = {
            -1: "Timeout waiting for echo response",
            -2: "Failed to detect pulse start or end",
        }
        try:
            distance = await self.px.get_distance()
            if distance < 0 and distance in errors:
                raise ValueError(errors.get(distance, "Unexpected distance error"))
            return distance
        except Exception as e:
            self.logger.error(f"Failed to get distance: {e}")
            raise
