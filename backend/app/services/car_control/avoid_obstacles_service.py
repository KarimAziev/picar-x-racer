import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.util.logger import Logger

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.services.distance_service import DistanceService


class AvoidObstaclesService:
    DEBOUNCE_INTERVAL = timedelta(seconds=1)

    def __init__(
        self,
        px: "PicarxAdapter",
        distance_service: "DistanceService",
    ):
        self.px = px
        self.logger = Logger(name=__name__)

        self.avoid_obstacles_task: Optional[asyncio.Task] = None
        self.last_toggle_time: Optional[datetime] = None
        self.avoid_obstacles_mode: bool = False
        self.distance_service = distance_service

    async def toggle_avoid_obstacles_mode(self) -> Optional[Dict[str, Any]]:
        """
        Toggles the mode for avoiding obstacles.
        """
        now = datetime.now(timezone.utc)
        if (
            self.last_toggle_time
            and (now - self.last_toggle_time) < self.DEBOUNCE_INTERVAL
        ):
            self.logger.info("Debounce: Too quick toggle of avoidObstacles detected.")
            return
        await asyncio.to_thread(self.reset_px)
        self.last_toggle_time = now
        self.avoid_obstacles_mode = not self.avoid_obstacles_mode

        if self.avoid_obstacles_mode:
            self.distance_service.interval = 0.1
        return {
            "avoidObstacles": self.avoid_obstacles_mode,
            "direction": 0,
            "servoAngle": 0,
            "camPan": 0,
            "camTilt": 0,
            "speed": 0,
            "maxSpeed": 30,
        }

    async def avoid_obstacles_subscriber(self, distance: float) -> None:
        POWER = 50
        SafeDistance = 40
        DangerDistance = 20
        if distance >= SafeDistance:
            await asyncio.to_thread(self.px.set_dir_servo_angle, 0)
            self.px.set_dir_servo_angle(0)
            self.px.forward(POWER)
        elif distance >= DangerDistance:
            self.px.set_dir_servo_angle(30)
            self.px.forward(POWER)
        else:
            self.px.set_dir_servo_angle(-30)
            self.px.backward(POWER)

    def reset_px(self) -> None:
        self.px.stop()
        self.px.set_cam_tilt_angle(0)
        self.px.set_cam_pan_angle(0)
        self.px.set_dir_servo_angle(0)
