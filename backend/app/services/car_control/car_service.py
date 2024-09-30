import asyncio
import json
from datetime import timedelta

from app.adapters.picarx_adapter import PicarxAdapter
from app.services.car_control.avoid_obstacles_service import AvoidObstaclesService
from app.services.car_control.calibration_service import CalibrationService
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket


class CarService(metaclass=SingletonMeta):
    DEBOUNCE_INTERVAL = timedelta(seconds=1)

    def __init__(self):
        self.logger = Logger(name=__name__)
        self.px = PicarxAdapter()
        self.avoid_obstacles_service = AvoidObstaclesService(self.px)
        self.calibration = CalibrationService(self.px)

    async def process_action(self, action: str, payload, websocket: WebSocket):
        """
        Processes specific actions received from WebSocket messages and performs the corresponding operations.

        Args:
            action (str): The action to be performed.
            payload: The payload data associated with the action.
            websocket (WebSocket): WebSocket connection instance.
        """

        self.logger.info(f"Action: '{action}' with payload '{payload}'")
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
        }

        calibrationData = None
        if action in calibration_actions_map:
            calibrationData = calibration_actions_map[action]()
            if calibrationData:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": (
                                "saveCalibration"
                                if action == "saveCalibration"
                                else "updateCalibration"
                            ),
                            "payload": calibrationData,
                        }
                    )
                )
        elif action in actions_map:
            func = actions_map[action]
            await func(payload, websocket)

        else:
            error_msg = f"Unknown action: {action}"
            self.logger.warning(error_msg)
            await websocket.send_text(json.dumps({"error": error_msg, "type": action}))

    async def handle_stop(self, payload, _: WebSocket):
        await self.px.stop()

    async def handle_set_servo_dir_angle(self, payload, _: WebSocket):
        angle = payload or 0
        await asyncio.to_thread(self.px.set_dir_servo_angle, angle)

    async def handle_set_cam_tilt_angle(self, payload, _):
        angle = payload
        await asyncio.to_thread(self.px.set_cam_tilt_angle, angle)

    async def handle_set_cam_pan_angle(self, payload, _: WebSocket):
        angle = payload
        await asyncio.to_thread(self.px.set_cam_pan_angle, angle)

    async def handle_avoid_obstacles(self, _, websocket: WebSocket):
        response = await self.avoid_obstacles_service.toggle_avoid_obstacles_mode()
        if response is not None:
            await websocket.send_text(json.dumps(response))

    async def handle_get_distance(self, _, websocket: WebSocket):
        await self.respond_with_distance("getDistance", websocket)

    async def handle_move(self, payload, _):
        """
        Handles move actions to control the car's direction and speed.

        Args:
            payload (dict): Payload containing direction and speed data.
        """
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
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
            await websocket.send_text(json.dumps(response))
        except Exception as e:
            error_response = {"type": action, "error": str(e)}
            await websocket.send_text(json.dumps(error_response))

    async def move(self, direction: int, speed: int):
        """
        Moves the car in the specified direction at the given speed.

        Args:
            direction (int): The direction to move the car (1 for forward, -1 for backward).
            speed (int): The speed at which to move the car.
        """

        self.logger.info(f"Moving {direction} with speed {speed}")
        if direction == 1:
            await asyncio.to_thread(self.px.forward, speed)
        elif direction == -1:
            await asyncio.to_thread(self.px.backward, speed)

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
