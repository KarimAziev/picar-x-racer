"""
A module to manage the Analog-to-Digital Converter (ADC) on the Raspberry Pi.

An Analog-to-Digital Converter (ADC) converts an analog signal into a digital signal.

This is essential for interpreting analog signals from sensors in digital devices like a Raspberry Pi.
"""

from typing import List, Union

from app.adapters.robot_hat.i2c import I2C
from app.util.logger import Logger

ADC_DEFAULT_ADDRESSES = [0x14, 0x15]

ADC_MAX_CHAN_VAL = 7
ADC_ALLOWED_CHANNELS = list(range(0, ADC_MAX_CHAN_VAL))
ADC_ALLOWED_CHANNELS_PIN_NAMES = [f"A{val}" for val in ADC_ALLOWED_CHANNELS]

ADC_ALLOWED_CHANNELS_DESCRIPTION = "Channel should be one of: " + ", ".join(
    ADC_ALLOWED_CHANNELS_PIN_NAMES + [f"{num}" for num in ADC_ALLOWED_CHANNELS]
)


class ADC(I2C):
    """
    A class to manage the Analog-to-Digital Converter (ADC) on the Raspberry Pi.

    An Analog-to-Digital Converter (ADC) converts an analog signal into a digital signal.
    This is essential for interpreting analog signals from sensors in digital devices like a Raspberry Pi.

    #### Key Concepts:

    - **Channel**: Each sensor or input signal is connected to an ADC channel.
    - **Resolution**: Determines how accurately the analog signal is converted to digital. A 12-bit ADC, for instance, could represent an analog signal with a value between 0 and 4095.
    - **MSB (Most Significant Byte)**: The byte in the data that has the highest value, representing the upper part of a numerical value.
    - **LSB (Least Significant Byte)**: The byte in the data that has the lowest value, representing the lower part of a numerical value.

    #### Example Usage
    ```python
    from app.adapters.robot_hat.adc import ADC

    # Initialize ADC on channel A0
    adc = ADC(channel="A4")

    # Read the ADC value
    value = adc.read()
    print(f"ADC Value: {value}")

    # Read the voltage
    voltage = adc.read_voltage()
    print(f"Voltage: {voltage} V")
    ```
    """

    def __init__(
        self,
        channel: Union[str, int],
        address: Union[int, List[int]] = ADC_DEFAULT_ADDRESSES,
        *args,
        **kwargs,
    ):
        """
        Initialize the ADC.

        Args:
            channel: Channel number (0-7 or A0-A7).
            address: The address or list of addresses of I2C devices.
        """

        super().__init__(address, *args, **kwargs)
        self._logger = Logger(__name__)
        if self.address is not None:
            self._logger.debug(f"ADC device address: 0x{self.address:02X}")
        else:
            self._logger.error("ADC device address not found")

        if (
            channel not in ADC_ALLOWED_CHANNELS_PIN_NAMES
            and channel not in ADC_ALLOWED_CHANNELS
        ):
            raise ValueError(
                f'Invalid ADC channel {channel}. ' + ADC_ALLOWED_CHANNELS_DESCRIPTION
            )

        if isinstance(channel, str):
            channel = int(channel[1:])

        channel = ADC_MAX_CHAN_VAL - channel
        # Convert to Register value
        self.channel = channel | 0x10

    def read_raw_value(self) -> int:
        """
        Retrieve and combine the ADC's Most Significant Byte (MSB) and Least Significant Byte (LSB).

        Returns:
            int: ADC value (0-4095).
        """
        # Write register address
        self.write([self.channel, 0, 0])
        msb, lsb = self.read(2)  # read two bytes
        self._logger.debug(
            "ADC Most Significant Byte: '%s', Least Significant Byte: '%s'", msb, lsb
        )

        # Combine MSB (Most Significant Byte) and LSB (Least Significant Byte)
        value = (msb << 8) + lsb
        self._logger.debug("ADC combined value: '%s'", value)
        return value

    def read_voltage(self) -> float:
        """
        Read the ADC value and convert to voltage.

        Returns:
            float: Voltage value (0-3.3 V).
        """
        # Read ADC value
        value = self.read_raw_value()

        # Convert to voltage
        voltage = value * 3.3 / 4095
        self._logger.debug(f"ADC raw voltage: {voltage}")
        return voltage
