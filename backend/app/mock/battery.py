class Battery:
    def __init__(
        self, initial_voltage_1=4.2, initial_voltage_2=4.2, discharge_rate=0.01
    ):
        """
        Initialize two 18650 batteries with initial voltages and a discharge rate.

        :param initial_voltage_1: Initial voltage of the first battery.
        :param initial_voltage_2: Initial voltage of the second battery.
        :param discharge_rate: Rate at which the battery discharges per session.
        """
        self.voltage_1 = initial_voltage_1
        self.voltage_2 = initial_voltage_2
        self.discharge_rate = discharge_rate

    def get_battery_voltage(self):
        """
        Get the current total voltage of the two batteries, simulating the discharge over time.

        :return: The total battery voltage in volts (V), which is a sum of two battery voltages.
        :rtype: float
        """
        total = self.voltage_1 + self.voltage_2

        if total > 6:
            self.voltage_2 -= self.discharge_rate
            self.voltage_1 -= self.discharge_rate

        total_voltage = max(6.0, self.voltage_1 + self.voltage_2)
        return total_voltage
