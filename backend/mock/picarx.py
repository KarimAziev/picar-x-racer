import random


class Ultrasonic:
    SOUND_SPEED = 343.3

    def __init__(self, trig, echo, timeout=0.1):
        self.trig = trig
        self.echo = echo
        self.timeout = timeout

    def read(self, times=10):
        for _ in range(times):
            a = random.choice([random.uniform(0.0, 200.0), -2, -1])
            if a != -1:
                return a
        return -1


class Picarx(object):
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
        trig, echo = ultrasonic_pins
        self.grayscale_pins = grayscale_pins
        self.motor_pins = motor_pins
        self.servo_pins = servo_pins
        self.ultrasonic = Ultrasonic(trig, echo)

    def set_dir_servo_angle(self, angle: int):
        print(f"Setting servo angle to {angle} degrees")

    def forward(self, speed: int):
        print(f"Moving forward with speed {speed}")

    def backward(self, speed: int):
        print(f"Moving backward with speed {speed}")

    def stop(self):
        print("Stopping")

    def set_cam_tilt_angle(self, angle: int):
        print(f"Setting camera tilt angle to {angle} degrees")

    def set_cam_pan_angle(self, angle: int):
        print(f"Setting camera pan angle to {angle} degrees")

    def get_distance(self):
        return self.ultrasonic.read()
