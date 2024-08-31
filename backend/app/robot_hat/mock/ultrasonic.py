import asyncio
from .pin_mock import Pin
import time


# 0 to 400 cm
class Ultrasonic:
    """
    Picar-x uses the `HC-SR04` ultrasonic distance sensor to provide non-contact distance measurements
    from 2 cm to 400 cm, with a ranging accuracy that can reach up to 3 mm.

    Each HC-SR04 module consists of an ultrasonic transmitter, a receiver, and a control circuit.

    ### Principle of Operation:

    1. Triggering the Sensor:
       - Send a high level to the `trig` (trigger) pin for at least 10 microseconds.
       - This initiates the module to send ultrasonic pulses at a frequency of 40 kHz.

    2. Sending and Receiving Pulses:
       - The transmitter emits the ultrasonic pulses and the receiver waits to detect the reflected pulses from any obstacle in the range.

    3. Calculating Distance:
       - If an obstacle is detected, the module sets a low level on the `echo` pin for 150 milliseconds.
       - Calculate the distance to the obstacle using the formula:

    ```
    distance = (time * sound_velocity) / 2
    ```
    Here, `time` is the measured pulse duration, and `sound velocity` is
    approximately 343.3 meters/second (or 340 meters/second depending on the ambient conditions and altitude).

    ### Pin Configuration:
    - `VCC`: Power supply (typically connected to 5V).
    - `Trig`: Trigger input (required by this class).
    - `Echo`: Echo output (required by this class).
    - `GND`: Ground (typically connected to ground).

    ### Attributes:
        - `SOUND_SPEED` (float): Speed of sound in m/s. Default is 343.3 m/s.
        - `timeout` (float): Maximum duration to wait for a pulse to return before timing out.

    ### Methods:
        - `__init__(self, trig: Pin, echo: Pin, timeout: float = 0.1)`: Initialize the Ultrasonic sensor.
        - `async _read(self) -> float`: Perform a single distance measurement.
        - `async read(self, times: int = 10) -> float`: Attempt to read the distance measurement multiple times and return the first successful read.
    """

    SOUND_SPEED = 343.3  # Speed of sound in m/s

    def __init__(self, trig: Pin, echo: Pin, timeout: float = 0.1):
        """
        Initialize the Ultrasonic sensor with specified trigger and echo pins.

        Args:
            trig (Pin): The pin connected to the TRIG of the ultrasonic sensor.
            echo (Pin): The pin connected to the ECHO of the ultrasonic sensor.
            timeout (float): Maximum duration to wait for a pulse to return. Default is 0.1 seconds.

        Raises:
            TypeError: If `trig` or `echo` is not an instance of `robot_hat.Pin`.
            RuntimeError: If the echo pin is not properly initialized.
        """
        if not isinstance(trig, Pin):
            raise TypeError("trig must be robot_hat.Pin object")
        if not isinstance(echo, Pin):
            raise TypeError("echo must be robot_hat.Pin object")

        self.timeout = timeout

        trig.close()
        echo.close()
        self.trig = Pin(trig._pin_num)
        self.echo = Pin(echo._pin_num, mode=Pin.IN, pull=Pin.PULL_DOWN)

    async def _read(self) -> float:
        """
        Perform a single distance measurement.

        Returns:
            float: The measured distance in centimeters. Returns -1 if there is a timeout,
                   and -2 if the measurement fails.

        Raises:
            RuntimeError: If the echo pin is not properly initialized.
        """
        self.trig.off()
        await asyncio.sleep(0.001)
        self.trig.on()
        await asyncio.sleep(0.00001)
        self.trig.off()

        pulse_end = 0
        pulse_start = 0
        timeout_start = time.time()

        if self.echo.gpio is None or not hasattr(self.echo.gpio, "value"):
            raise RuntimeError("Echo pin is not properly initialized")

        while self.echo.gpio.value == 0:
            pulse_start = time.time()
            if pulse_start - timeout_start > self.timeout:
                return -1

        while self.echo.gpio.value == 1:
            pulse_end = time.time()
            if pulse_end - timeout_start > self.timeout:
                return -1

        if pulse_start == 0 or pulse_end == 0:
            return -2

        during = pulse_end - pulse_start
        cm = round(during * self.SOUND_SPEED / 2 * 100, 2)
        return cm

    async def read(self, times: int = 10) -> float:
        """
        Attempt to read the distance measurement multiple times and return the first successful read.

        Args:
            times (int): Number of attempts to take a reading. Default is 10.

        Returns:
            float: The measured distance in centimeters. Returns -1 if all attempts fail.
        """
        for _ in range(times):
            a = await self._read()
            if a != -1:
                return a
        return -1
