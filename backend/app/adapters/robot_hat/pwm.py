"""
A module to manage Pulse Width Modulation (PWM) which allows you to control the power delivered to devices
like LEDs, motors, and other actuators.

Pulse Width Modulation (PWM) is a technique used to encode information or control the amount of power
delivered to a device. It does this by changing the width of the digital pulses applied to the device.

- **High Pulse**: The duration when the signal is high.
- **Low Pulse**: The duration when the signal is low.
"""

import math
from typing import List, Optional, Union

from app.adapters.robot_hat.i2c import I2C
from app.adapters.robot_hat.pin_descriptions import pin_descriptions
from app.util.logger import Logger

timer: list[dict[str, int]] = [{"arr": 1}] * 7

PRESCALER_SQRT_OFFSET = (
    5  # The offset applied to the square root result in prescaler calculation.
)
PRESCALER_SEARCH_WINDOW = 10  # The window size of prescaler values to search for the optimal prescaler-period pair.


class PWM(I2C):
    """
    A class to manage Pulse Width Modulation (PWM) - a technique used to encode a message into a pulsing signal.

    In electronics, it often refers to a method of reducing the average power
    delivered by an electrical signal by effectively chopping it up into
    discrete parts.

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

    REG_PSC2 = 0x50
    """Prescaler register prefix"""

    REG_ARR2 = 0x54
    """Period registor prefix"""

    ADDR = [0x14, 0x15, 0x16]
    """List of possible I2C addresses"""

    CLOCK = 72000000.0
    """Clock frequency in Hz"""

    def __init__(self, channel: Union[int, str], address=None, *args, **kwargs):
        """
        Initialize the PWM module.

        Args:
            channel (int or str): PWM channel number (0-19/P0-P19).
            address (Optional[List[int]]): I2C device address or list of addresses.
        """
        if address is None:
            super().__init__(self.ADDR, *args, **kwargs)
        else:
            super().__init__(address, *args, **kwargs)

        self._chan_desc = pin_descriptions.get(
            (
                channel
                if isinstance(channel, str)
                else f"P{channel}" if isinstance(channel, int) else "unknown"
            ),
            "unknown",
        )

        self.logger = Logger(__name__)

        if isinstance(channel, str):
            if channel.startswith("P"):
                channel = int(channel[1:])
            else:
                msg = f'PWM channel should be between [P0, P19], not "{channel}"'
                self.logger.error(msg)
                raise ValueError(msg)
        if isinstance(channel, int):
            if channel > 15 or channel < 0:
                msg = f'channel must be in range of 0-19, not "{channel}"'
                raise ValueError(msg)

        if isinstance(self.address, int):
            self.logger.debug(
                "Initted PWM at the address {%s}",
                hex(self.address),
            )
        else:
            self.logger.warning(
                "PWM address %s is not found. channel: %s", address, channel
            )

        self.channel = channel
        if channel < 16:
            self.timer = int(channel / 4)
        elif channel == 16 or channel == 17:
            self.timer = 4
        elif channel == 18:
            self.timer = 5
        elif channel == 19:
            self.timer = 6
        self._pulse_width = 0
        self._freq = 50
        self.freq(50)

    def _i2c_write(self, reg: int, value: int):
        """
        Write a 16-bit value to a specified I2C register.

        This method writes to a device over the I2C bus. It takes a 16-bit value, splits it into
        a high byte (most significant byte) and a low byte (least significant byte), and writes
        these two bytes sequentially to the given 8-bit register.

        The operation is typically used to configure or send data to devices such as sensors,
        memory chips, or display controllers via an I2C interface.

        Args:
            reg (int): An 8-bit register address on the I2C device where the data will be written.
            value (int): A 16-bit integer value that will be split into two 8-bit bytes. The
                         most significant byte (high byte) will be sent first, followed by the
                         least significant byte (low byte).

        I2C Write Format:
            The data sent via the `write` method is structured as:
            [register address, high byte, low byte]

            - The high byte is extracted by shifting the 16-bit value 8 bits to the right.
            - The low byte is extracted using a bitwise AND with 0xFF to mask the upper bits.

        Example:
            If `reg = 0x05` and `value = 0x1234`:
                - High byte (`value_h`) = 0x12
                - Low byte (`value_l`) = 0x34
            The data written would be [0x05, 0x12, 0x34].

        Returns:
            None
        """
        value_h = (
            value >> 8
        )  # High byte: Shift right 8 bits to extract the most significant byte
        value_l = (
            value & 0xFF
        )  # Low byte: Mask with 0xFF to keep only the least significant byte
        # Write the register address followed by the high and low bytes to the I2C device

        self.logger.debug(
            "[%s]: writing 16 bit %s (%s) high byte: %s (%s) low byte: %s, (%s)",
            self._chan_desc,
            value,
            hex(value),
            value_h,
            hex(value_h),
            value_l,
            hex(value_l),
        )
        self.write([reg, value_h, value_l])

    def freq(self, freq=None):
        """
        Set or get the PWM frequency.

        This method dynamically finds appropriate values for the prescaler and period to achieve the requested PWM frequency.
        The method evaluates a range of prescaler values along with the corresponding period and picks the combination
        that yields the frequency closest to the requested value.

        Note: The frequency should be in the range of 0 to 65535 Hz, but realistic values are usually lower.

        Args:
            freq (Optional[float]): Desired PWM frequency in Hertz. If not provided, it returns the current frequency.

        Returns:
            float: The current PWM frequency if no argument is provided.

        Example:
            ```python
            pwm_controller.freq(1000)  # Set PWM frequency to 1 kHz
            current_freq = pwm_controller.freq()  # Get the current frequency
            ```

        Method Details:
            1. It calculates several prescaler and period values based on the provided frequency.
            2. For each combination, it checks how close the actual frequency (derived from prescaler and period)
               is to the desired frequency.
            3. It selects the best prescaler and period values that produce the closest result, and updates hardware registers.
        """
        if freq is None:
            return self._freq

        self._freq = int(freq)

        result_ap: List[List[int]] = []
        acurracy_list: List[float] = []

        # Estimate prescaler values and adjust for accuracy
        st = max(1, int(math.sqrt(self.CLOCK / self._freq)) - PRESCALER_SQRT_OFFSET)

        for psc in range(st, st + PRESCALER_SEARCH_WINDOW):
            arr = int(self.CLOCK / self._freq / psc)
            result_ap.append([psc, arr])
            acurracy_list.append(abs(self._freq - self.CLOCK / psc / arr))

        i = acurracy_list.index(min(acurracy_list))

        psc, arr = result_ap[i]

        self.logger.debug(
            "[{%s}]: frequency {%s} -> prescaler {%s}, period: {%s}",
            self._chan_desc,
            self._freq,
            psc,
            arr,
        )

        self.prescaler(psc)
        self.period(arr)

    def prescaler(self, prescaler: Optional[Union[float, int]] = None):
        """
        Set or get the PWM prescaler value.

        The prescaler divides the clock input, which directly affects the speed of the PWM cycle.
        A larger prescaler value means the PWM cycles more slowly.

        Args:
            prescaler (Optional[int]): The prescaler value to set. It should be between 0 and 65535.
                                       If not provided, the method will return the current prescaler value.

        Returns:
            int: The current prescaler value if no argument is passed.

        ## Example:
        ```python
        pwm_controller.prescaler(1200)  # Set prescaler to 1200
        current_prescaler = pwm_controller.prescaler()  # Get the current prescaler
        ```
        """
        if prescaler is None:
            return self._prescaler

        self._prescaler = round(prescaler)
        self._freq = self.CLOCK / self._prescaler / timer[self.timer]["arr"]
        if self.timer < 4:
            reg = self.REG_PSC + self.timer
        else:
            reg = self.REG_PSC2 + self.timer - 4
        self.logger.debug(
            "[%s]: Set prescaler to PWM %s at timer %s to register: %s, global timer: %s",
            self._chan_desc,
            self._prescaler - 1,
            self.timer,
            hex(reg),
            timer,
        )
        self._i2c_write(reg, self._prescaler - 1)

    def period(self, arr: Optional[int] = None):
        """
        Set or get the PWM period value.

        The period defines the total number of clock ticks in one complete PWM cycle (both high and low pulses).
        A longer period results in a slower cycle, while a shorter period makes the PWM frequency faster.

        Args:
            arr (Optional[int]): Auto-Reload Register (ARR). New period value (0-65535).
            If not provided, retrieves current period.

        ### Visual Representation

        Imagine the PWM signal as a repeating cycle of ON and OFF states.
        The Auto-Reload Register value determines how long the entire cycle takes:

        ```
        |<----------- Period (arr) ----------->|
        |                                      |
        |   High Time    |    Low Time         |
        |    (ON)        |     (OFF)           |
        |*************** |---------------------|
        ```

        - **Period**: Total duration of one cycle (High Time + Low Time), determined by `arr`.

        - **Frequency**: Number of cycles per second, calculated as `Frequency = Clock / arr`.

        Returns:
            int: The current period value if no argument is passed.

        Example:
            ```python
            pwm_controller.period(4095)  # Set period to 4095
            current_period = pwm_controller.period()  # Get current period
            ```
        """
        global timer
        if arr is None:
            return timer[self.timer]["arr"]

        arr = round(arr)

        timer[self.timer]["arr"] = arr
        self._freq = self.CLOCK / self._prescaler / arr

        if self.timer < 4:
            reg = self.REG_ARR + self.timer
        else:
            reg = self.REG_ARR2 + self.timer - 4

        self.logger.debug(
            "[%s]: Set period to PWM %s at timer %s to register: %s, global timer: %s",
            self._chan_desc,
            arr,
            self.timer,
            hex(reg),
            timer,
        )
        self._i2c_write(reg, arr)

    def pulse_width(self, pulse_width=None):
        """
        Set or get the pulse width.

        Args:
            pulse_width (Optional[float]): Pulse width value (0-65535).
            Leave blank to get the current pulse width.

        Returns:
            float: The current pulse width value.
        """
        if pulse_width is None:
            return self._pulse_width

        self._pulse_width = int(pulse_width)
        reg = self.REG_CHN + self.channel
        self.logger.debug(
            "[%s]: writing pulse width %s  to register: %s global timer: %s",
            self._chan_desc,
            self._pulse_width,
            hex(reg),
            timer,
        )
        self._i2c_write(reg, self._pulse_width)

    def pulse_width_percent(self, pulse_width_percent=None):
        """
        Set or get the pulse width percentage.

        Args:
            pulse_width_percent (Optional[float]): Pulse width percentage (0-100).
            Leave blank to get the current pulse width percentage.

        Returns:
            float: The current pulse width percentage.
        """
        global timer
        if pulse_width_percent is None:
            return self._pulse_width_percent

        self._pulse_width_percent = pulse_width_percent
        temp = self._pulse_width_percent / 100.0
        pulse_width = temp * timer[self.timer]["arr"]
        self.pulse_width(pulse_width)


def test():
    import time

    p = PWM(0)
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
    p = PWM("P0")
    p.pulse_width_percent(50)
    # while True:
    #     p.pulse_width_percent(50)


if __name__ == "__main__":
    test2()
