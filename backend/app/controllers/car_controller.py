import asyncio
import inspect
import json
from datetime import datetime, timedelta, timezone

from app.controllers.calibration_controller import CalibrationController
from app.util.logger import Logger
from app.util.platform_adapters import Picarx
from app.util.singleton_meta import SingletonMeta
from fastapi import WebSocket


class CarController(metaclass=SingletonMeta):
    DEBOUNCE_INTERVAL = timedelta(seconds=1)

    def __init__(self):
        self.px = Picarx()
        self.logger = Logger(name=__name__)
        self.calibration = CalibrationController(self.px)
        self.last_toggle_time = None
        self.avoid_obstacles_mode = False
        self.avoid_obstacles_task = None

    async def stop(self):
        await asyncio.to_thread(self.px.stop)

    async def handle_move(self, payload, websocket):
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
        await self.move(direction, speed)

    async def handle_set_servo_dir_angle(self, payload, websocket):
        angle = payload or 0
        await asyncio.to_thread(self.px.set_dir_servo_angle, angle)

    async def handle_stop(self, payload, websocket):
        await self.stop()

    async def handle_set_cam_tilt_angle(self, payload, websocket):
        angle = payload
        await asyncio.to_thread(self.px.set_cam_tilt_angle, angle)

    async def handle_set_cam_pan_angle(self, payload, websocket):
        angle = payload
        await asyncio.to_thread(self.px.set_cam_pan_angle, angle)

    async def handle_avoid_obstacles(self, payload, websocket):
        await self.toggle_avoid_obstacles_mode(websocket)

    async def handle_get_distance(self, payload, websocket):
        await self.respond_with_distance("getDistance", websocket)

    async def process_action(self, action: str, payload, websocket: WebSocket):
        """
        Processes specific actions received from WebSocket messages and performs the corresponding operations.

        Args:
            action (str): The action to be performed.
            payload: The payload data associated with the action.
            websocket (WebSocket): WebSocket connection instance.
        """

        self.logger.info(f"Action: '{action}' with payload {payload}")
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

    async def handle_move(self, payload):
        """
        Handles move actions to control the car's direction and speed.

        Args:
            payload (dict): Payload containing direction and speed data.
        """
        direction = payload.get("direction", 0)
        speed = payload.get("speed", 0)
        await self.move(direction, speed)

    async def toggle_avoid_obstacles_mode(self, websocket: WebSocket):
        """
        Toggles the mode for avoiding obstacles.

        Args:
            websocket (WebSocket): WebSocket connection instance.
        """

        now = datetime.now(timezone.utc)
        if (
            self.last_toggle_time
            and (now - self.last_toggle_time) < self.DEBOUNCE_INTERVAL
        ):
            self.logger.info("Debounce: Too quick toggle of avoidObstacles detected.")
            return
        await self.cancel_avoid_obstacles_task()
        await self.handle_px_reset(websocket)
        self.last_toggle_time = now
        self.avoid_obstacles_mode = not self.avoid_obstacles_mode

        response = {"payload": self.avoid_obstacles_mode, "type": "avoidObstacles"}
        await websocket.send_text(json.dumps(response))

        if self.avoid_obstacles_mode:
            self.avoid_obstacles_task = asyncio.create_task(self.avoid_obstacles())

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

    async def handle_px_reset(self, websocket: WebSocket):
        """
        Resets the car's servo and camera to default angles.

        Args:
            websocket (WebSocket): WebSocket connection instance.
        """

        await self.stop()
        self.px.set_cam_tilt_angle(0)
        self.px.set_cam_pan_angle(0)
        self.px.set_dir_servo_angle(0)
        await websocket.send_text(
            json.dumps(
                {
                    "payload": {
                        "direction": 0,
                        "servoAngle": 0,
                        "camPan": 0,
                        "camTilt": 0,
                        "speed": 0,
                        "maxSpeed": 30,
                    },
                    "type": "update",
                }
            )
        )

    async def cancel_avoid_obstacles_task(self):
        """
        Cancels the background task for avoiding obstacles, if running.
        """

        if self.avoid_obstacles_task:
            try:
                self.avoid_obstacles_task.cancel()
                await self.avoid_obstacles_task
            except asyncio.CancelledError:
                self.logger.info("Avoid obstacles task was cancelled")
                self.avoid_obstacles_task = None

    async def avoid_obstacles(self):
        """
        Background task that continuously checks for obstacles and navigates around them.
        """

        POWER = 50
        SafeDistance = 40
        DangerDistance = 20
        try:
            while True:
                value = await self.px.ultrasonic.read()
                distance = round(value, 2)
                self.logger.info(f"distance: {distance}")
                if distance >= SafeDistance:
                    self.px.set_dir_servo_angle(0)
                    self.px.forward(POWER)
                elif distance >= DangerDistance:
                    self.px.set_dir_servo_angle(30)
                    self.px.forward(POWER)
                    await asyncio.sleep(0.1)
                else:
                    self.px.set_dir_servo_angle(-30)
                    self.px.backward(POWER)
                    await asyncio.sleep(0.5)
        finally:
            self.px.forward(0)

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
