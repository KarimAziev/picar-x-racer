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
    from app.adapters.pidog.pidog import Pidog
    from app.services.connection_service import ConnectionService
    from app.services.distance_service import DistanceService


class PidogService(metaclass=SingletonMeta):

    def __init__(
        self,
        pidog: "Pidog",
        connection_manager: "ConnectionService",
        distance_service: "DistanceService",
    ):
        self.logger = Logger(name=__name__)
        self.pidog = pidog
        self.connection_manager = connection_manager
        self.distance_service = distance_service
        self.user_settings_file = PX_SETTINGS_FILE
        self.settings_file = (
            self.user_settings_file
            if os.path.exists(self.user_settings_file)
            else DEFAULT_USER_SETTINGS
        )
        self.settings: Dict[str, Any] = load_json_file(self.settings_file)
        self.speed = 0
        self.max_speed: int = self.settings.get("max_speed", 90)
        self.direction = 0
        self.servo_dir_angle = 0
        self.cam_pan_angle = 0
        self.cam_tilt_angle = 0

    async def broadcast(self):
        await self.connection_manager.broadcast_json(self.broadcast_payload)

    @property
    def current_state(self):
        """
        Returns key metrics of the current state as a dictionary.
        """
        return {
            "speed": self.speed,
            "maxSpeed": self.max_speed,
            "direction": self.direction,
            "servoAngle": self.servo_dir_angle,
            "camPan": self.cam_pan_angle,
            "camTilt": self.cam_tilt_angle,
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
        calibration_actions_map = {}

        actions_map = {
            "move": self.handle_move,
            "stop": self.handle_stop,
            "setServoDirAngle": self.handle_set_servo_dir_angle,
            "setCamTiltAngle": self.handle_set_cam_tilt_angle,
            "setCamPanAngle": self.handle_set_cam_pan_angle,
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

    async def handle_set_servo_dir_angle(self, payload, _: WebSocket):
        """
        Update leg positions for turning (servo direction). This won't trigger forward/back motion.
        """
        angle = payload or 0
        if -30 <= angle <= 30:
            if angle != 0 and self.speed == 0:
                self.speed = 98
            if self.direction == 0:
                self.direction = 1
            if angle < 0:
                self.pidog.do_action('turn_left_backward' if self.direction == -1 else 'turn_left', speed=self.speed)
                await asyncio.to_thread(self.pidog.do_action, 'turn_left_backward' if self.direction == -1 else 'turn_left', speed=self.speed)
            elif angle > 0:
                await asyncio.to_thread(self.pidog.do_action, 'turn_right_backward' if self.direction == -1 else 'turn_right', speed=self.speed)
                self.servo_dir_angle = angle
            elif self.speed > 0:
                await asyncio.to_thread(self.pidog.do_action, 'backward' if self.direction == -1 else 'forward', speed=self.speed)
                self.servo_dir_angle = angle
            else:
                await asyncio.to_thread(self.pidog.body_stop)
                self.speed = 0
                self.direction = 0

            self.servo_dir_angle = angle
        else:
            raise ValueError(
                "Servo direction angle must be between -30 and 30 degrees."
            )

    async def handle_stop(self, payload, _: WebSocket):
        """
        Stops the robot immediately.
        """
        await asyncio.to_thread(self.pidog.body_stop)
        self.speed = 0
        self.direction = 0


    async def handle_set_cam_tilt_angle(self, payload, _):
        """
        Tilt the head up or down using the pitch axis.
        """
        angle = payload or 0
        if self.pidog.HEAD_PITCH_MIN <= angle <= self.pidog.HEAD_PITCH_MAX:
            await asyncio.to_thread(
                self.pidog.head_move, [[0, 0, angle]], immediately=True, speed=80
            )
            self.cam_tilt_angle = angle
        else:
            raise ValueError("Tilt angle must be between -45 and 30 degrees.")

    async def handle_set_cam_pan_angle(self, payload, _):
        """
        Pan the head left or right using the yaw axis.
        """
        angle = payload or 0
        if self.pidog.HEAD_YAW_MIN <= angle <= self.pidog.HEAD_YAW_MAX:
            await asyncio.to_thread(
                self.pidog.head_move, [[angle, 0, 0]], immediately=True, speed=80
            )
            self.cam_pan_angle = angle
        else:
            raise ValueError("Pan angle must be between -90 and 90 degrees.")

    async def handle_get_distance(self, _, websocket: WebSocket):
        await self.respond_with_distance("getDistance", websocket)

    async def handle_max_speed(self, payload: int, websocket: WebSocket):
        self.max_speed = payload
        if self.speed > self.max_speed:
            await self.move(self.direction, self.max_speed)

    async def handle_move(self, payload, _):
        """
        Handles move actions to control the dog's direction and speed.

        Args:
            payload (dict): Payload containing direction and speed data.
        """
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
        if self.direction != direction or speed != self.speed:
            await self.move(direction, speed)

    async def respond_with_distance(self, action: str, websocket: WebSocket):
        """
        Responds with the distance measured by the dog's ultrasonic sensor.

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
        Moves the dog in the specified direction at the given speed.

        Args:
            direction (int): The direction to move the dog (1 for forward, -1 for backward).
            speed (int): The speed at which to move the dog.
        """
        if direction == 1:
            await asyncio.to_thread(self.pidog.do_action, "forward", speed=speed)
        elif direction == -1:
            await asyncio.to_thread(self.pidog.do_action, "backward", speed=speed)

        self.speed = speed

        self.direction = direction

    async def get_distance(self):
        """
        Measures and returns the distance using the dog's ultrasonic sensor.

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
            distance = await asyncio.to_thread(self.pidog.read_distance)
            if distance < 0 and distance in errors:
                raise ValueError(errors.get(distance, "Unexpected distance error"))
            return distance
        except Exception as e:
            self.logger.error(f"Failed to get distance: {e}")
            raise
