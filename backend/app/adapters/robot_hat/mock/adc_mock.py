from app.adapters.robot_hat.mock.i2c_mock import I2C
from app.mock.battery import Battery

battery = Battery()


class ADC(I2C):
    """
    Analog to digital converter
    """

    ADDR = [0x14, 0x15]

    def __init__(self, chn, address=None, *args, **kwargs):
        """
        Analog to digital converter

        :param chn: channel number (0-7/A0-A7)
        :type chn: int/str
        """
        if address is not None:
            super().__init__(address, *args, **kwargs)
        else:
            super().__init__(self.ADDR, *args, **kwargs)
        self.logger.debug(f"ADC device address: 0x{self.address:02X}")

        if isinstance(chn, str):
            # If chn is a string, assume it's a pin name, remove A and convert to int
            if chn.startswith("A"):
                chn = int(chn[1:])
            else:
                raise ValueError(f'ADC channel should be between [A0, A7], not "{chn}"')
        # Make sure channel is between 0 and 7
        if chn < 0 or chn > 7:
            raise ValueError(f'ADC channel should be between [0, 7], not "{chn}"')
        chn = 7 - chn
        # Convert to Register value
        self.chn = chn | 0x10

    def read(self):
        """
        Read the ADC value

        :return: ADC value(0-4095)
        :rtype: int
        """
        # Write register address
        self.write([self.chn, 0, 0])
        # Read values
        msb, lsb = super().read(2)

        # Combine MSB and LSB
        value = (msb << 8) + lsb
        self.logger.debug(f"Read value: {value}")
        return value

    def read_voltage(self):
        """
        Generate the total battery voltage by simulating the reading from two 18650 batteries.

        This function simulates the behavior of reading battery voltage from two 18650 lithium-ion batteries,
        which typically have a nominal voltage of around 3.7V but can range between 3.0V (fully discharged)
        and 4.2V (fully charged). It returns a randomly generated value within this range for each battery
        and sums them to provide the total voltage.

        Example:
            If the first battery voltage is 3.8V and the second battery voltage is 4.1V,
            the total voltage returned by this function would be 3.8 + 4.1 = 7.9V.

        :return: The total battery voltage in volts (V), which is a sum of two battery voltages.
        :rtype: float
        """
        return battery.get_battery_voltage()
