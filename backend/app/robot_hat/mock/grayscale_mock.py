from app.robot_hat.mock.adc_mock import ADC

from typing import Optional, List


class Grayscale_Module:
    """
    The Grayscale Module provides 3-channel grayscale sensing, allowing for the detection of line status or intensity using three individual ADC channels.

    ### Channels:
    - `LEFT` (int): Left channel index.
    - `MIDDLE` (int): Middle channel index.
    - `RIGHT` (int): Right channel index.

    ### Attributes:
    - `REFERENCE_DEFAULT` (list): Default reference values for the grayscale sensors.

    ### Methods:
    - `__init__(self, pin0: ADC, pin1: ADC, pin2: ADC, _: Optional[int] = None)`: Initializes the Grayscale Module.
    - `reference(self, ref: Optional[List[int]] = None) -> List[int]`: Sets or gets the reference values for the sensors.
    - `read_status(self, datas: Optional[List[int]] = None) -> List[int]`: Reads the status of the lines (white or black).
    - `read(self, channel: Optional[int] = None) -> List[int]`: Reads the grayscale data from the specified channel or all channels.

    ### Example usage

    ```python
    grayscale = Grayscale_Module(pin0, pin1, pin2)

    # Get the status of all lines:
    status = grayscale.read_status()

    # Read the grayscale value from the left channel:
    left_value = grayscale.read(Grayscale_Module.LEFT)
    ```
    """

    LEFT = 0
    """Left Channel"""
    MIDDLE = 1
    """Middle Channel"""
    RIGHT = 2
    """Right Channel"""

    REFERENCE_DEFAULT = [1000] * 3

    def __init__(self, pin0: ADC, pin1: ADC, pin2: ADC, _: Optional[int] = None):
        """
        Initialize Grayscale Module

        :param pin0: ADC object for channel 0
        :type pin0: ADC
        :param pin1: ADC object for channel 1
        :type pin1: ADC
        :param pin2: ADC object for channel 2
        :type pin2: ADC
        """
        self.pins = (pin0, pin1, pin2)
        for i, pin in enumerate(self.pins):
            if not isinstance(pin, ADC):
                raise TypeError(f"pin{i} must be an ADC instance")
        self._reference = self.REFERENCE_DEFAULT

    def reference(self, ref: Optional[List] = None) -> list:
        """
        Get or set reference values

        :param ref: Reference values, or None to get current reference values
        :type ref: list
        :return: Reference values
        :rtype: list
        """
        if ref is not None:
            if isinstance(ref, list) and len(ref) == 3:
                self._reference = ref
            else:
                raise TypeError("ref parameter must be a list with 3 elements.")
        return self._reference

    def read_status(self, datas: Optional[List[int]] = None) -> List[int]:
        """
        Read line status

        :param datas: Grayscale data list, or None to read from sensors
        :type datas: list
        :return: List of line status, 0 for white, 1 for black
        :rtype: list
        """
        if self._reference is None:
            raise ValueError("Reference value is not set")
        if datas is None:
            datas = self.read()
        return [0 if data > self._reference[i] else 1 for i, data in enumerate(datas)]

    def read(self, channel: Optional[int] = None) -> List[int]:
        """
        Read a channel or all data points.

        :param channel: Channel to read, or None to read all channels
        :type channel: int/None
        :return: List of grayscale data
        :rtype: list
        """
        if channel is None:
            return [self.pins[i].read() for i in range(3)]
        else:
            return self.pins[channel].read()


if __name__ == "__main__":
    adc0 = ADC(0)
    adc1 = ADC(1)
    adc2 = ADC(2)
    grayscale = Grayscale_Module(adc0, adc1, adc2)

    # Test reading values and statuses
    print(grayscale.read())
    print(grayscale.read_status())
    grayscale.reference([800, 800, 800])
    print(grayscale.read_status())
