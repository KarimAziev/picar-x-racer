import asyncio
import random
import time
from app.config.logging_config import setup_logger

logger = setup_logger(__name__)


class Ultrasonic:
    SOUND_SPEED = 343.3

    def __init__(self, trig, echo, timeout=0.1):
        self.trig = trig
        self.echo = echo
        self.timeout = timeout
        self.dir_current_angle = 0

    async def _read(self):
        await asyncio.sleep(0.001)
        await asyncio.sleep(0.00001)

        return random.choice([random.uniform(0.0, 400.0)])

    async def read(self, times=10):
        for _ in range(times):
            a = await self._read()
            if a != -1:
                return a
        return -1


class Picarx(object):
    DEFAULT_LINE_REF = [1000, 1000, 1000]
    DEFAULT_CLIFF_REF = [500, 500, 500]

    DIR_MIN = -30
    DIR_MAX = 30
    CAM_PAN_MIN = -90
    CAM_PAN_MAX = 90
    CAM_TILT_MIN = -35
    CAM_TILT_MAX = 65

    PERIOD = 4095
    PRESCALER = 10
    TIMEOUT = 0.02

    ultrasonic: Ultrasonic
    CONFIG = "/opt/picar-x/picar-x.conf"

    def __init__(
        self,
        servo_pins: list = ["P0", "P1", "P2"],
        motor_pins: list = ["D4", "D5", "P12", "P13"],
        grayscale_pins: list = ["A0", "A1", "A2"],
        ultrasonic_pins: list = ["D2", "D3"],
        _: str = CONFIG,
    ):
        time.sleep(0.2)
        trig, echo = ultrasonic_pins
        self.grayscale_pins = grayscale_pins
        self.motor_pins = motor_pins
        self.servo_pins = servo_pins
        self.dir_current_angle = 0
        self.speed = 0
        self.ultrasonic = Ultrasonic(trig, echo)

    def set_dir_servo_angle(self, angle: int):
        logger.info(f"Setting servo angle to {angle} degrees")

    def forward(self, speed: int):
        logger.info(f"Moving forward with speed {speed}")

    def backward(self, speed: int):
        logger.info(f"Moving backward with speed {speed}")

    async def stop(self):
        for _ in range(2):
            await asyncio.sleep(0.002)
        logger.info("Stopped")

    def set_cam_tilt_angle(self, angle: int):
        logger.info(f"Setting camera tilt angle to {angle} degrees")

    def set_cam_pan_angle(self, angle: int):
        logger.info(f"Setting camera pan angle to {angle} degrees")

    async def get_distance(self):
        return await self.ultrasonic.read()
