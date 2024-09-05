"""
A module to manage Servo motors using PWM (Pulse Width Modulation) control.
 - Control the angle of the servo motor.
 - Set the pulse width for precise control.
"""

from app.util.logger import Logger

from .pwm import PWM
from .utils import mapping


class Servo(PWM):
    """
    A class to manage Servo motors using PWM control.

    ### Key Features:
    - Control the angle of the servo motor.
    - Set the pulse width for precise control.

    ### Attributes:
        - `MAX_PW` (int): Maximum pulse width in microseconds (default is 2500).
        - `MIN_PW` (int): Minimum pulse width in microseconds (default is 500).
        - `FREQ` (int): Frequency for PWM signals (default is 50 Hz).
        - `PERIOD` (int): PWM period value (default is 4095).

    ### Methods:
        - `__init__(self, channel, address=None, *args, **kwargs)`: Initialize the servo motor class.
        - `angle(self, angle)`: Set the angle of the servo motor.
        - `pulse_width_time(self, pulse_width_time)`: Set the pulse width of the servo motor.

    #### Understanding Servo Control
    Servo motors are widely used in robotics and automation for precise control of angular position.
    They operate using PWM signals, where the pulse width determines the angle of the servo shaft.

    - **Pulse Width**: The time the signal stays high in a PWM cycle.
    - **Frequency**:  The number of PWM cycles per second, typically set to 50 Hz for servo motors.

    The angle is determined by the duration of the high pulse within the PWM cycle. For instance:
    - A 1.5 ms pulse might center the servo at 0 degrees.
    - A shorter or longer pulse will move the servo to -90 degrees or +90 degrees, respectively.

    #### Playing with Servo Motors
    You can control servo motors to achieve various angles using the `angle` method. Adjusting the pulse width
    allows fine control over the servo's position, enabling applications like robotic arms, steering systems, and more.

    Here's a visual representation:

    ```
    ^
    | B     _______         _______         _______
    | r    |       |       |       |       |       |
    | i    |       |       |       |       |       |
    | g    |       |_______|       |_______|       |__
    | h    ^
    | t    |<-1ms->|<-1ms->|<-1ms->|<-1ms->|<-1ms->
    ```

    In the above visualization:
    - The duration of the high signal determines the position of the servo motor.

    """

    MAX_PW = 2500
    """Maximum pulse width in microseconds"""
    MIN_PW = 500
    """Minimum pulse width in microseconds"""
    FREQ = 50
    """Frequency for PWM signals in Hz"""
    PERIOD = 4095
    """PWM period value"""

    def __init__(self, channel, address=None, *args, **kwargs):
        """
        Initialize the servo motor class.

        Args:
            channel (int or str): PWM channel number (0-14 or P0-P14).
            address (Optional[List[int]]): I2C device address or list of addresses.
        """
        super().__init__(channel, address, *args, **kwargs)
        self.logger = Logger(__name__)
        self.logger.debug(f"channel {channel} address f{address}")
        self.period(self.PERIOD)
        prescaler = self.CLOCK / self.FREQ / self.PERIOD
        self.prescaler(prescaler)

    def angle(self, angle):
        """
        Set the angle of the servo motor.

        Args:
            angle (float): Desired angle (-90 to 90 degrees).

        Raises:
            ValueError: If the angle is not an int or float.
        """
        if not (isinstance(angle, int) or isinstance(angle, float)):
            msg = "Angle value should be int or float value, not %s" % type(angle)
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.debug(f"Set angle to: {angle}")
        if angle < -90:
            angle = -90
        if angle > 90:
            angle = 90
        self.logger.debug(f"Set angle to: {angle}")
        pulse_width_time = mapping(angle, -90, 90, self.MIN_PW, self.MAX_PW)
        self.logger.debug(f"Pulse width: {pulse_width_time}")
        self.pulse_width_time(pulse_width_time)

    def pulse_width_time(self, pulse_width_time):
        """
        Set the pulse width of the servo motor.

        Args:
            pulse_width_time (float): Pulse width time in microseconds (500 to 2500).
        """
        self.logger.debug(f"pulse_width_time: {pulse_width_time}")
        if pulse_width_time > self.MAX_PW:
            pulse_width_time = self.MAX_PW
        if pulse_width_time < self.MIN_PW:
            pulse_width_time = self.MIN_PW
        self.logger.debug(f"Adjusted pulse_width_time: {pulse_width_time}")
        pwr = pulse_width_time / 20000.0
        self.logger.debug(f"pulse width rate: {pwr}")
        value = int(pwr * self.PERIOD)
        self.logger.debug(f"pulse width value: {value}")
        self.pulse_width(value)
