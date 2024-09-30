"""
A module to manage Pulse Width Modulation (PWM) which allows you to control the power delivered to devices
like LEDs, motors, and other actuators.

Pulse Width Modulation (PWM) is a technique used to encode information or control the amount of power
delivered to a device. It does this by changing the width of the digital pulses applied to the device.

- **High Pulse**: The duration when the signal is high.
- **Low Pulse**: The duration when the signal is low.
"""

import math
from typing import TYPE_CHECKING

from app.config.platform import is_os_raspberry
from app.util.logger import Logger

if is_os_raspberry:
    from app.adapters.robot_hat.i2c import I2C
else:
    from app.adapters.robot_hat.mock.i2c_mock import I2C


timer: list[dict[str, int]] = [{"arr": 1}] * 4

if TYPE_CHECKING:
    from app.adapters.robot_hat.i2c import I2C


class PWM(I2C):
    """
    A class to manage Pulse Width Modulation (PWM) which allows you to control the power delivered to devices
    like LEDs, motors, and other actuators.

    ### Key Features:
    - Set and get the frequency of PWM signals.
    - Set and get the prescaler and period values for fine-tuning.
    - Set and get the pulse width and its percentage.

    ### Attributes:
        - `REG_CHN` (int): Channel register prefix (default is 0x20).
        - `REG_PSC` (int): Prescaler register prefix (default is 0x40).
        - `REG_ARR` (int): Period register prefix (default is 0x44).
        - `ADDR` (List[int]): List of I2C addresses that the PWM controller can use.
        - `CLOCK` (float): Clock frequency for the PWM module.

    ### Methods:
        - `__init__(self, channel, address=None, *args, **kwargs)`: Initialize the PWM module.
        - `_i2c_write(self, reg, value)`: Write to an I2C register.
        - `freq(self, freq=None)`: Set or get the PWM frequency.
        - `prescaler(self, prescaler=None)`: Set or get the prescaler value.
        - `period(self, arr=None)`: Set or get the period value.
        - `pulse_width(self, pulse_width=None)`: Set or get the pulse width value.
        - `pulse_width_percent(self, pulse_width_percent=None)`: Set or get the pulse width percentage.

    #### What is PWM?
    Pulse Width Modulation (PWM) is a technique used to encode information or control the amount of power
    delivered to a device. It does this by changing the width of the digital pulses applied to the device.

    - **High Pulse**: The duration when the signal is high.
    - **Low Pulse**: The duration when the signal is low.

    #### Playing with PWM
    Using PWM, you can easily control devices like LEDs, motors, and more. Adjust the 'pulse width' or 'frequency'
    to control the behavior of these devices. For example, controlling the brightness of an LED or the speed of a motor.

    Here's a visual representation of PWM signals:

    ```
    ^
    |          ____       ____       ____
    |         |    |     |    |     |    |
    |         |    |     |    |     |    |
    | ____    |    |_____|    |_____|    |_____|
    |<---T--->|<---T--->|<---T--->|<---T--->
    ```

    In the above visualization:
    - T is the period.
    - The signal goes high for a fraction of the period (pulse width) and low for the remaining period.

    """

    REG_CHN = 0x20
    """Channel register prefix"""
    REG_PSC = 0x40
    """Prescaler register prefix"""
    REG_ARR = 0x44
    """Period register prefix"""

    ADDR = [0x14, 0x15]
    """List of possible I2C addresses"""

    CLOCK = 72000000.0
    """Clock frequency in Hz"""

    def __init__(self, channel, address=None, *args, **kwargs):
        """
        Initialize the PWM module.

        Args:
            channel (int or str): PWM channel number (0-15 or P0-P15).
            address (Optional[List[int]]): I2C device address or list of addresses.
        """
        if address is None:
            super().__init__(self.ADDR, *args, **kwargs)
        else:
            super().__init__(address, *args, **kwargs)

        self.logger = Logger(__name__)

        if isinstance(channel, str):
            if channel.startswith("P"):
                channel = int(channel[1:])
            else:
                msg = f'PWM channel should be between [P0, P15], not "{channel}"'
                self.logger.error(msg)
                raise ValueError(msg)
        if isinstance(channel, int):
            if channel > 15 or channel < 0:
                msg = f'channel must be in range of 0-15, not "{channel}"'
                raise ValueError(msg)

        self.channel = channel
        self.timer = int(channel / 4)
        self._pulse_width = 0
        self._freq = 50
        self.freq(50)

    def _i2c_write(self, reg, value):
        """
        Write a value to an I2C register.

        Args:
            reg (int): Register address.
            value (int): Value to write.

        Returns:
            None
        """
        value_h = value >> 8
        value_l = value & 0xFF
        self.write([reg, value_h, value_l])

    def freq(self, freq=None):
        """
        Set or get the PWM frequency.

        Args:
            freq (Optional[float]): Frequency in Hz (0-65535). Leave blank to get the current frequency.

        Returns:
            float: The current frequency.
        """
        if freq is None:
            return self._freq

        self._freq = int(freq)
        result_ap = []  # List of [prescaler, period]
        result_acy = []  # Accuracy list

        st = int(math.sqrt(self.CLOCK / self._freq))
        st -= 5
        if st <= 0:
            st = 1
        for psc in range(st, st + 10):
            arr = int(self.CLOCK / self._freq / psc)
            result_ap.append([psc, arr])
            result_acy.append(abs(self._freq - self.CLOCK / psc / arr))

        i = result_acy.index(min(result_acy))
        psc, arr = result_ap[i]
        self.logger.debug(f"Prescaler: {psc}, Period: {arr}")
        self.prescaler(psc)
        self.period(arr)

    def prescaler(self, prescaler=None):
        """
        Set or get the prescaler value.

        Args:
            prescaler (Optional[int]): Prescaler value (0-65535). Leave blank to get the current prescaler value.

        Returns:
            int: The current prescaler value.
        """
        if prescaler is None:
            return self._prescaler

        self._prescaler = round(prescaler)
        self._freq = self.CLOCK / self._prescaler / timer[self.timer]["arr"]
        reg = self.REG_PSC + self.timer
        self.logger.debug(f"Set prescaler to: {self._prescaler}")
        self._i2c_write(reg, self._prescaler - 1)

    def period(self, arr=None):
        """
        Set or get the period value.

        Args:
            arr (Optional[int]): Period value (0-65535). Leave blank to get the current period value.

        Returns:
            int: The current period value.
        """
        global timer
        if arr is None:
            return timer[self.timer]["arr"]

        timer[self.timer]["arr"] = round(arr)
        self._freq = self.CLOCK / self._prescaler / timer[self.timer]["arr"]
        reg = self.REG_ARR + self.timer
        self.logger.debug(f"Set period to: {timer[self.timer]['arr']}")
        self._i2c_write(reg, timer[self.timer]["arr"])

    def pulse_width(self, pulse_width=None):
        """
        Set or get the pulse width.

        Args:
            pulse_width (Optional[float]): Pulse width value (0-65535). Leave blank to get the current pulse width.

        Returns:
            float: The current pulse width value.
        """
        if pulse_width is None:
            return self._pulse_width

        self._pulse_width = int(pulse_width)
        reg = self.REG_CHN + self.channel
        self._i2c_write(reg, self._pulse_width)

    def pulse_width_percent(self, pulse_width_percent=None):
        """
        Set or get the pulse width percentage.

        Args:
            pulse_width_percent (Optional[float]): Pulse width percentage (0-100). Leave blank to get the current pulse width percentage.

        Returns:
            float: The current pulse width percentage.
        """
        global timer
        if pulse_width_percent is None:
            return self._pulse_width_percent

        self._pulse_width_percent = pulse_width_percent
        pulse_width = (pulse_width_percent / 100.0) * timer[self.timer]["arr"]
        self.pulse_width(pulse_width)


def test():
    import time

    p = PWM(0, debug_level="debug")
    p.period(1000)
    p.prescaler(10)
    # p.pulse_width(2048)
    while True:
        for i in range(0, 4095, 10):
            p.pulse_width(i)
            print(i)
            time.sleep(1 / 4095)
        time.sleep(1)
        for i in range(4095, 0, -10):
            p.pulse_width(i)
            print(i)
            time.sleep(1 / 4095)
        time.sleep(1)


def test2():
    p = PWM("P0", debug_level="debug")
    p.pulse_width_percent(50)
    # while True:
    #     p.pulse_width_percent(50)


if __name__ == "__main__":
    test2()
