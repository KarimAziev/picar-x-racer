from .i2c import I2C


class ADC(I2C):
    """
    A class to manage the Analog-to-Digital Converter (ADC) on the Raspberry Pi.

    ### Key Features:
    - Read analog values from different channels.
    - Convert analog values to digital and voltage readings.

    ### Attributes:
        - `ADDR` (list): List of possible I2C addresses for the ADC.
        - `chn` (int): The specific ADC channel to read from.

    ### Methods:
        - `__init__(self, chn, address=None, *args, **kwargs)`: Initialize the ADC.
        - `read(self)`: Read the ADC value (0-4095).
        - `read_voltage(self)`: Read the ADC value and convert it to voltage.

    #### What is ADC?
    An Analog-to-Digital Converter (ADC) converts an analog signal into a digital signal.
    This is essential for interpreting analog signals from sensors in digital devices like a Raspberry Pi.

    #### How They Work
    - **Channel**: Each sensor or input signal is connected to an ADC channel.
    - **Resolution**: Determines how accurately the analog signal is converted to digital. A 12-bit ADC, for instance, could represent an analog signal with a value between 0 and 4095.
    - **MSB (Most Significant Byte)**: The byte in the data that has the highest value, representing the upper part of a numerical value.
    - **LSB (Least Significant Byte)**: The byte in the data that has the lowest value, representing the lower part of a numerical value.

    #### Example Usage
    Imagine you're reading the voltage from a sensor connected to channel A0 on your ADC. This class allows you to retrieve that value and convert it into a readable voltage.

    ```python
    from app.robot_hat.adc import ADC

    # Initialize ADC on channel A0
    adc = ADC(chn="A0")

    # Read the ADC value
    value = adc.read()
    print(f"ADC Value: {value}")

    # Read the voltage
    voltage = adc.read_voltage()
    print(f"Voltage: {voltage} V")
    ```
    """

    ADDR = [0x14, 0x15]
    """List of possible I2C addresses for the ADC."""

    def __init__(self, chn, address=None, *args, **kwargs):
        """
        Initialize the ADC.

        Args:
            chn (Union[int, str]): Channel number (0-7 or A0-A7).
            address (int, optional): I2C device address.
        """
        if address is not None:
            super().__init__(address, *args, **kwargs)
        else:
            super().__init__(self.ADDR, *args, **kwargs)
        self.logger.debug(f"ADC device address: 0x{self.address:02X}")

        if isinstance(chn, str):
            # If chn is a string, assume it's a pin name, remove "A" and convert to int
            if chn.startswith("A"):
                chn = int(chn[1:])
            else:
                raise ValueError(f'ADC channel should be between [A0, A7], not "{chn}"')
        # Ensure channel is between 0 and 7
        if chn < 0 or chn > 7:
            raise ValueError(f'ADC channel should be between [0, 7], not "{chn}"')
        chn = 7 - chn
        # Convert to Register value
        self.chn = chn | 0x10

    def read(self):
        """
        Read the ADC value.

        Returns:
            int: ADC value (0-4095).
        """
        # Write register address
        self.write([self.chn, 0, 0])
        # Read values
        msb, lsb = super().read(2)

        # Combine MSB (Most Significant Byte) and LSB (Least Significant Byte)
        value = (msb << 8) + lsb
        self.logger.debug(f"Read value: {value}")
        return value

    def read_voltage(self):
        """
        Read the ADC value and convert to voltage.

        Returns:
            float: Voltage value (0-3.3 V).
        """
        # Read ADC value
        value = self.read()

        # Convert to voltage
        voltage = value * 3.3 / 4095
        self.logger.debug(f"Read voltage: {voltage}")
        return voltage
