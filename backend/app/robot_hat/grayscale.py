from .adc import ADC
from typing import Optional


class Grayscale_Module(object):
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

    ### Read the grayscale value from the left channel:
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

        :param pin0: ADC object or int for channel 0
        :type pin0: robot_hat.ADC/int
        :param pin1: ADC object or int for channel 1
        :type pin1: robot_hat.ADC/int
        :param pin2: ADC object or int for channel 2
        :type pin2: robot_hat.ADC/int
        :param reference: reference voltage
        :type reference: 1*3 list, [int, int, int]
        """
        self.pins = (pin0, pin1, pin2)
        for i, pin in enumerate(self.pins):
            if not isinstance(pin, ADC):
                raise TypeError(f"pin{i} must be robot_hat.ADC")
        self._reference = self.REFERENCE_DEFAULT

    def reference(self, ref: Optional[list] = None) -> list:
        """
        Get Set reference value

        :param ref: reference value, None to get reference value
        :type ref: list
        :return: reference value
        :rtype: list
        """
        if ref is not None:
            if isinstance(ref, list) and len(ref) == 3:
                self._reference = ref
            else:
                raise TypeError("ref parameter must be 1*3 list.")
        return self._reference

    def read_status(self, datas: Optional[list] = None) -> list:
        """
        Read line status

        :param datas: list of grayscale datas, if None, read from sensor
        :type datas: list
        :return: list of line status, 0 for white, 1 for black
        :rtype: list
        """
        if self._reference == None:
            raise ValueError("Reference value is not set")
        if datas == None:
            datas = self.read()
        return [0 if data > self._reference[i] else 1 for i, data in enumerate(datas)]

    def read(self, channel: Optional[int] = None) -> list:
        """
        Read a channel or all datas.

        :param channel: channel to read, leave empty to read all. 0, 1, 2 or Grayscale_Module.LEFT, Grayscale_Module.CENTER, Grayscale_Module.RIGHT
        :type channel: int/None
        :return: list of grayscale data
        :rtype: list
        """
        if channel == None:
            return [self.pins[i].read() for i in range(3)]
        else:
            return self.pins[channel].read()
