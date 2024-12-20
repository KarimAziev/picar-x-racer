import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.util.logger import Logger

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter


class AvoidObstaclesService:
    DEBOUNCE_INTERVAL = timedelta(seconds=1)

    def __init__(self, px: "PicarxAdapter"):
        self.px = px
        self.logger = Logger(name=__name__)

        self.avoid_obstacles_task: Optional[asyncio.Task] = None
        self.last_toggle_time: Optional[datetime] = None
        self.avoid_obstacles_mode: bool = False

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
        await self.cancel_avoid_obstacles_task()
        await asyncio.to_thread(self.reset_px)
        self.last_toggle_time = now
        self.avoid_obstacles_mode = not self.avoid_obstacles_mode

        if self.avoid_obstacles_mode:
            self.avoid_obstacles_task = asyncio.create_task(self.avoid_obstacles())
        return {
            "avoidObstacles": self.avoid_obstacles_mode,
            "direction": 0,
            "servoAngle": 0,
            "camPan": 0,
            "camTilt": 0,
            "speed": 0,
            "maxSpeed": 30,
        }

    async def cancel_avoid_obstacles_task(self) -> None:
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

    async def avoid_obstacles(self) -> None:
        POWER = 50
        SafeDistance = 40
        DangerDistance = 20
        try:
            while True:
                value = await asyncio.to_thread(self.px.ultrasonic.read)
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

    def reset_px(self) -> None:
        self.px.stop()
        self.px.set_cam_tilt_angle(0)
        self.px.set_cam_pan_angle(0)
        self.px.set_dir_servo_angle(0)
