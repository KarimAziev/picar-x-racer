from app.adapters.robot_hat.battery import Battery as BatteryOrig


class Battery(BatteryOrig):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        """
        Initialize two 18650 batteries with initial voltages and a discharge rate.
        """
        super().__init__(*args, **kwargs)
        self.voltage_1 = 4.2
        self.voltage_2 = 4.2
        self.discharge_rate = 0.01

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
