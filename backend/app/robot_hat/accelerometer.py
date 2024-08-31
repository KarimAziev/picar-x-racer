from .i2c import I2C
from typing import Union, List, Optional


class ADXL345(I2C):
    """
    The ADXL345 is a small, thin, low power, 3-axis accelerometer with high resolution (13-bit) measurement at up to ±16g.

    Digital output data is formatted as 16-bit two's complement and is accessible through either:
    - a SPI (3- or 4-wire)
    - I2C digital interface.

    ### Attributes:
        - `X` (int): Represents the X-axis.
        - `Y` (int): Represents the Y-axis.
        - `Z` (int): Represents the Z-axis.
        - `ADDR` (int): Default I2C address for the ADXL345.
        - `_REG_DATA_X` (int): Register address for X-axis data.
        - `_REG_DATA_Y` (int): Register address for Y-axis data.
        - `_REG_DATA_Z` (int): Register address for Z-axis data.
        - `_REG_POWER_CTL` (int): Register address for power control.
        - `_AXISES` (list): List of register addresses for X, Y, Z axis data.

    ### Methods:
        - `__init__(self, *args, address: int = ADDR, bus: int = 1, **kwargs)`: Initializes the ADXL345 sensor.
        - `read(self, axis: Optional[int] = None) -> Union[float, List[float]]`: Reads the specified axis data or all axis data.
        - `_read(self, axis: int) -> float`: Reads data from a specified axis register.

    ### Example usage:
    ```python
    adxl = ADXL345()
    x, y, z = adxl.read()  # Reads all axis data
    x_value = adxl.read(ADXL345.X)  # Reads X-axis data
    ```
    """

    X = 0
    """X"""
    Y = 1
    """Y"""
    Z = 2
    """Z"""
    ADDR = 0x53
    _REG_DATA_X = 0x32  # X-axis data 0 (6 bytes for X/Y/Z)
    _REG_DATA_Y = 0x34  # Y-axis data 0 (6 bytes for X/Y/Z)
    _REG_DATA_Z = 0x36  # Z-axis data 0 (6 bytes for X/Y/Z)
    _REG_POWER_CTL = 0x2D  # Power-saving features control
    _AXISES = [_REG_DATA_X, _REG_DATA_Y, _REG_DATA_Z]

    def __init__(self, *args, address: int = ADDR, bus: int = 1, **kwargs):
        """
        Initialize ADXL345

        :param address: address of the ADXL345
        :type address: int
        """
        super().__init__(address=address, bus=bus, *args, **kwargs)
        self.address = address

    def read(
        self, axis: Optional[int] = None
    ) -> Union[float, List[Union[float, None]], None]:
        """
        Read an axis from ADXL345

        :param axis: read value(g) of an axis, ADXL345.X, ADXL345.Y or ADXL345.Z, None for all axis
        :type axis: int
        :return: value of the axis, or list of all axis
        :rtype: float/list
        """
        if axis is None:
            return [self._read(i) for i in range(3)]
        else:
            return self._read(axis)

    def _read(self, axis: int) -> Union[float, None]:
        raw_2 = 0
        result = super().read()
        data = (0x08 << 8) + self._REG_POWER_CTL
        if result:
            self.write(data)
        self.mem_write(0, 0x31)
        self.mem_write(8, 0x2D)
        raw = self.mem_read(2, self._AXISES[axis])
        # The first value read is always 0, so read it again.
        self.mem_write(0, 0x31)
        self.mem_write(8, 0x2D)
        raw = self.mem_read(2, self._AXISES[axis])
        if raw:
            if raw[1] >> 7 == 1:
                raw_1 = raw[1] ^ 128 ^ 127
                raw_2 = (raw_1 + 1) * -1
            else:
                raw_2 = raw[1]
            g = raw_2 << 8 | raw[0]
            value = g / 256.0
            return value
