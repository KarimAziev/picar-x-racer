from app.robot_hat.mock.pwm_mock import PWM


def mapping(x, in_min, in_max, out_min, out_max):
    """
    Map value from one range to another range

    :param x: value to map
    :type x: float/int
    :param in_min: input minimum
    :type in_min: float/int
    :param in_max: input maximum
    :type in_max: float/int
    :param out_min: output minimum
    :type out_min: float/int
    :param out_max: output maximum
    :type out_max: float/int
    :return: mapped value
    :rtype: float/int
    """
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class Servo(PWM):
    """Servo motor class"""

    MAX_PW = 2500
    MIN_PW = 500
    FREQ = 50
    PERIOD = 4095

    def __init__(self, channel, address=None, *args, **kwargs):
        """
        Initialize the servo motor class

        :param channel: PWM channel number(0-14/P0-P14)
        :type channel: int/str
        """
        super().__init__(channel, address, *args, **kwargs)
        self.period(self.PERIOD)
        prescaler = self.CLOCK / self.FREQ / self.PERIOD
        self.prescaler(prescaler)

    def angle(self, angle):
        """
        Set the angle of the servo motor

        :param angle: angle(-90~90)
        :type angle: float
        """
        if not (isinstance(angle, int) or isinstance(angle, float)):
            raise ValueError(
                f"Angle value should be int or float value, not {type(angle)}"
            )
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
        Set the pulse width of the servo motor

        :param pulse_width_time: pulse width time(500~2500)
        :type pulse_width_time: float
        """
        if pulse_width_time > self.MAX_PW:
            pulse_width_time = self.MAX_PW
        if pulse_width_time < self.MIN_PW:
            pulse_width_time = self.MIN_PW

        pwr = pulse_width_time / 20000
        self.logger.debug(f"pulse width rate: {pwr}")
        value = int(pwr * self.PERIOD)
        self.logger.debug(f"pulse width value: {value}")
        self.pulse_width(value)
