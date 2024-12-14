from typing import List, Union

from app.adapters.robot_hat.adc import ADC, ADC_DEFAULT_ADDRESSES
from app.util.logger import Logger


class Battery(ADC):
    """
    A class to manage battery-specific readings using the ADC.

    This class extends the ADC functionality and adds battery-specific logic, such as
    scaling the voltage to 10V systems (e.g., common in battery applications).
    """

    CACHE_SECONDS = 5

    def __init__(
        self,
        channel: Union[str, int],
        address: Union[int, List[int]] = ADC_DEFAULT_ADDRESSES,
        *args,
        **kwargs,
    ):
        """
        Initialize the Battery object.

        Args:
            channel: ADC channel connected to the battery.
            address: The address or list of addresses of I2C devices (defaults to ADC_DEFAULT_ADDRESSES).
        """
        super().__init__(channel, address, *args, **kwargs)
        self._logger = Logger(__name__)

    def get_battery_voltage(self) -> float:
        """
        Read and scale ADC voltage readings to a 0-10V system.

        Returns:
            float: The scaled battery voltage in volts.
        """
        voltage = self.read_voltage()
        scaled_voltage = round(voltage * 3, 2)  # Scale the 0-3.3V reading to 0-10V
        self._logger.debug(f"Battery voltage (scaled to 0-10V): {scaled_voltage} V")
        return scaled_voltage
