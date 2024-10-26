from app.adapters.robot_hat.adc import ADC as ADC_real
from app.mock.battery import Battery

battery = Battery()


class ADC(ADC_real):
    """
    Analog to digital converter
    """

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
        voltage = battery.get_battery_voltage() / 3
        self.logger.info(
            "Read voltage mock: %s",
            voltage,
        )
        return voltage
