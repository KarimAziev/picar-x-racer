"""
A module to manage communication between a Raspberry Pi and devices that support the I2C protocol.

I2C stands for Inter-Integrated Circuit and is a type of synchronous communication protocol, that allows multiple integrated circuits (ICs) to communicate with one another using just two lines:

- **SCL (Clock line)**: Synchronizes the data transfer between the devices.
- **SDA (Data line)**: Carries the data between the devices.

#### How They Work
- **Master**: The device that initiates and controls the communication.
- **Slave**: The device that responds to the master's request.
- Each I2C device has a unique address that allows the master to communicate with specific devices.
"""

from typing import Any, List, Optional, Union

from app.robot_hat.address_descriptions import (
    get_address_description,
    get_value_description,
)
from app.util.logger import Logger
from smbus2 import SMBus

from .utils import run_command


def _retry_wrapper(func):
    def wrapper(self: "I2C", *args: Any, **kwargs: Any) -> Any:
        for _ in range(self.RETRY):
            try:
                return func(self, *args, **kwargs)
            except OSError:
                self.logger.debug(f"OSError: {func.__name__}")
                continue
        else:
            return False

    return wrapper


class I2C(object):
    """
    A class to manage communication between a Raspberry Pi and devices that
    support the I2C protocol. I2C stands for Inter-Integrated Circuit and is
    a type of synchronous communication protocol.

    ### Key Features:
    - Read and write functions for I2C communication.
    - Scan for connected I2C devices.
    - Retry mechanism for robust communication.

    ### Attributes:
        - `RETRY` (int): Number of retry attempts for communication.
        - `logger` (Logger): Logger instance for logging messages.
        - `_bus` (int): I2C bus number (default is 1).
        - `_smbus` (SMBus): SMBus instance for I2C operations.
        - `address` (int): I2C device address.

    ### Methods:
        - `__init__(self, address: Optional[int], bus: int = 1)`: Initialize the I2C bus.
        - `_write_byte(self, data: int)`: Write a single byte to the I2C device.
        - `_write_byte_data(self, reg: int, data: int)`: Write a byte of data to a specific register.
        - `_write_word_data(self, reg: int, data: int)`: Write a word of data to a specific register.
        - `_write_i2c_block_data(self, reg: int, data: list)`: Write blocks of data to a specific register.
        - `_read_byte(self)`: Read a single byte from the I2C device.
        - `_read_byte_data(self, reg: int)`: Read a byte of data from a specific register.
        - `_read_word_data(self, reg: int)`: Read a word of data from a specific register.
        - `_read_i2c_block_data(self, reg: int, num: int)`: Read blocks of data from a specific register.
        - `is_ready(self) -> bool`: Check if the I2C device is ready.
        - `scan(self) -> list`: Scan the I2C bus for devices.
        - `write(self, data: Union[int, list, bytearray])`: Write data to the I2C device.
        - `read(self, length: int = 1) -> list`: Read data from the I2C device.
        - `mem_write(self, data: Union[int, list, bytearray], memaddr: int)`: Write data to a specific register.
        - `mem_read(self, length: int, memaddr: int) -> list`: Read data from a specific register.
        - `is_avaliable(self) -> bool`: Check if the I2C device is available.

    #### What is I2C?
    I2C (Inter-Integrated Circuit) is a communication protocol that allows multiple integrated circuits (ICs) to communicate with one another using just two lines:
    - **SCL (Clock line)**: Synchronizes the data transfer between the devices.
    - **SDA (Data line)**: Carries the data between the devices.

    #### How They Work
    - **Master**: The device that initiates and controls the communication.
    - **Slave**: The device that responds to the master's request.
    - Each I2C device has a unique address that allows the master to communicate with specific devices.

    #### Playing with I2C
    Imagine you have several sensors and devices connected to your Raspberry Pi using I2C. You can easily read and write data to them using the I2C class. For example, you can:
    - Scan the I2C bus to identify connected devices.
    - Write data to and read data from specific registers of these devices.

    Here's a visual representation of scanning for devices:

    ```
         0 1 2 3 4 5 6 7 8 9 a b c d e f
    00:          -- -- -- -- -- -- -- -- -- -- -- --
    10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    70: -- -- -- -- 15 -- -- 17
    ```

    In the above scan, devices were found at addresses `0x15` and `0x17`.

    """

    RETRY = 5
    """Number of retry attempts for I2C communication"""

    def __init__(
        self,
        address: Optional[Union[int, List[int]]] = None,
        bus: int = 1,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize the I2C bus.

        Args:
            address (Optional[int]): I2C device address.
            bus (int): I2C bus number. Default is 1.
        """

        super().__init__(*args, **kwargs)

        self.logger = Logger(name=__name__)
        self._bus = bus
        self._smbus = SMBus(self._bus)

        if isinstance(address, list):
            connected_devices = self.scan()
            for _addr in address:
                if _addr in connected_devices:
                    self.address = _addr
                    break
            else:
                self.address = address[0]
        else:
            self.address = address

    @_retry_wrapper
    def _write_byte(self, data: int) -> Optional[int]:
        """
        Write a single byte to the I2C device.

        Args:
            data (int): Byte of data to write.

        Returns:
            None
        """

        description = get_value_description(data)
        self.logger.debug(f"_write_byte: [0x{data:02X}] {description}")
        result = self._smbus.write_byte(self.address, data) if self.address else None
        return result

    @_retry_wrapper
    def _write_byte_data(self, reg: int, data: int) -> Optional[int]:
        """
        Write a byte of data to a specific register.

        Args:
            reg (int): Register address.
            data (int): Byte of data to write.

        Returns:
            None
        """

        reg_description = get_address_description(reg)
        data_description = get_value_description(data)
        self.logger.debug(
            f"_write_byte_data: [0x{reg:02X}] {reg_description} [0x{data:02X}] {data_description}"
        )
        if self.address:
            return self._smbus.write_byte_data(self.address, reg, data)

    @_retry_wrapper
    def _write_word_data(self, reg: int, data: int) -> Optional[int]:
        """
        Write a word of data to a specific register.

        Args:
            reg (int): Register address.
            data (int): Word of data to write.

        Returns:
            None
        """

        reg_description = get_address_description(reg)
        data_description = get_value_description(data)
        self.logger.debug(
            f"_write_word_data: [0x{reg:02X}] {reg_description} [0x{data:04X}] {data_description}"
        )
        if self.address:
            return self._smbus.write_word_data(self.address, reg, data)

    @_retry_wrapper
    def _write_i2c_block_data(self, reg: int, data: List[int]) -> Optional[int]:
        """
        Write blocks of data to a specific register.

        Args:
            reg (int): Register address.
            data (list): List of data blocks to write.

        Returns:
            None
        """

        reg_description = get_address_description(reg)
        data_descriptions = [get_value_description(d) for d in data]
        self.logger.debug(
            f"_write_i2c_block_data: [0x{reg:02X}] {reg_description} {[f'0x{i:02X} {descr}' for i, descr in zip(data, data_descriptions)]}"
        )
        if self.address:
            return self._smbus.write_i2c_block_data(self.address, reg, data)

    @_retry_wrapper
    def _read_byte(self) -> Optional[int]:
        """
        Read a single byte from the I2C device.

        Returns:
            int: Byte read from the device, or None if error.
        """

        if self.address:
            result = self._smbus.read_byte(self.address)
            description = get_value_description(result)
            self.logger.debug(f"_read_byte: [0x{result:02X}] {description}")
            return result

    @_retry_wrapper
    def _read_byte_data(self, reg: int) -> Optional[int]:
        """
        Read a byte of data from a specific register.

        Args:
            reg (int): Register address.

        Returns:
            int: Byte read from the register, or None if error.
        """

        if self.address:
            result = self._smbus.read_byte_data(self.address, reg)
            reg_description = get_address_description(reg)
            result_description = get_value_description(result)
            self.logger.debug(
                f"_read_byte_data: [0x{reg:02X}] {reg_description} [0x{result:02X}] {result_description}"
            )
            return result

    @_retry_wrapper
    def _read_word_data(self, reg: int) -> Optional[List[int]]:
        """
        Read a word of data from a specific register.

        Args:
            reg (int): Register address.

        Returns:
            list: Word read from the register in two bytes, or None if error.
        """

        if self.address:
            result = self._smbus.read_word_data(self.address, reg)
            result_list = [result & 0xFF, (result >> 8) & 0xFF]
            reg_description = get_address_description(reg)
            result_description = get_value_description(result)
            self.logger.debug(
                f"_read_word_data: [0x{reg:02X}] {reg_description} [0x{result:04X}] {result_description}"
            )
            return result_list

    @_retry_wrapper
    def _read_i2c_block_data(self, reg: int, num: int) -> Optional[List[int]]:
        """
        Read blocks of data from a specific register.

        Args:
            reg (int): Register address.
            num (int): Number of blocks to read.

        Returns:
            list: List of blocks read from the register, or None if error.
        """

        if self.address:
            result = self._smbus.read_i2c_block_data(self.address, reg, num)
            reg_description = get_address_description(reg)
            result_descriptions = [get_value_description(r) for r in result]
            self.logger.debug(
                f"_read_i2c_block_data: [0x{reg:02X}] {reg_description} {[f'0x{i:02X} {descr}' for i, descr in zip(result, result_descriptions)]}"
            )
            return result

    @_retry_wrapper
    def is_ready(self) -> bool:
        """
        Check if the I2C device is ready.

        Returns:
            bool: True if the I2C device is ready, False otherwise.
        """

        addresses = self.scan()
        if self.address in addresses:
            return True
        return False

    def scan(self) -> List[int]:
        """
        Scan the I2C bus for devices.

        Returns:
            list: List of I2C addresses of devices found.
        """

        try:
            cmd = f"i2cdetect -y {self._bus}"
            # Run the i2cdetect command
            _, output = run_command(cmd)
            self.logger.debug(f"i2cdetect\n{output}")
            # Parse the output
            outputs = output.split("\n")[1:]
            addresses = []
            addresses_str = []
            for tmp_addresses in outputs:
                if tmp_addresses == "":
                    continue
                tmp_addresses = tmp_addresses.split(":")[1]
                # Split the addresses into a list
                tmp_addresses = tmp_addresses.strip().split(" ")
                for address in tmp_addresses:
                    if address != "--":
                        addresses.append(int(address, 16))
                        addresses_str.append(f"0x{address}")
            self.logger.debug(f"Connected i2c device: {addresses_str}")
            return addresses
        except Exception as err:
            self.logger.error(f"Scan error {err}")
            return []

    def write(self, data: Union[int, List[int], bytearray]) -> None:
        """
        Write data to the I2C device.

        Args:
            data (Union[int, list, bytearray]): Data to write.

        Raises:
            ValueError: If the data is not an int, list, or bytearray.
        """

        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, int):
            if data == 0:
                data_all = [0]
            else:
                data_all = []
                while data > 0:
                    data_all.append(data & 0xFF)
                    data >>= 8
        elif isinstance(data, list):
            data_all = data
        else:
            msg = f"write data must be int, list, or bytearray, not {type(data)}"
            self.logger.error(msg)
            raise ValueError(msg)

        if len(data_all) == 1:
            data = data_all[0]
            description = get_value_description(data)
            self.logger.debug(f"write: single byte [0x{data:02X}] {description}")
            self._write_byte(data)
        elif len(data_all) == 2:
            reg = data_all[0]
            data = data_all[1]
            reg_description = get_address_description(reg)
            data_description = get_value_description(data)
            self.logger.debug(
                f"write: register [0x{reg:02X}] {reg_description} data [0x{data:02X}] {data_description}"
            )
            self._write_byte_data(reg, data)
        elif len(data_all) == 3:
            reg = data_all[0]
            data = (data_all[2] << 8) + data_all[1]
            reg_description = get_address_description(reg)
            data_description = get_value_description(data)
            self.logger.debug(
                f"write: register [0x{reg:02X}] {reg_description} word [0x{data:04X}] {data_description}"
            )
            self._write_word_data(reg, data)
        else:
            reg = data_all[0]
            data = list(data_all[1:])
            reg_description = get_address_description(reg)
            data_descriptions = [get_value_description(d) for d in data]
            self.logger.debug(
                f"write: register [0x{reg:02X}] {reg_description} block {[f'0x{i:02X} {descr}' for i, descr in zip(data, data_descriptions)]}"
            )
            self._write_i2c_block_data(reg, data)

    def read(self, length: int = 1):
        """
        Read data from the I2C device.

        Args:
            length (int): Number of bytes to receive. Default is 1.

        Returns:
            list: List of bytes read from the I2C device.
        """

        if not isinstance(length, int):
            msg = f"length must be int, not {type(length)}"
            self.logger.error(msg)
            raise ValueError(msg)

        result = []
        for _ in range(length):
            byte = self._read_byte()
            if byte is not None:
                description = get_value_description(byte)
                result.append(byte)
                self.logger.debug(f"read: byte [0x{byte:02X}] {description}")
            else:
                self.logger.debug(f"read: byte [None]")
        return result

    def mem_write(self, data: Union[int, List[int], bytearray], memaddr: int) -> None:
        """
        Write data to a specific register address.

        Args:
            data (Union[int, list, bytearray]): Data to write.
            memaddr (int): Register address.

        Raises:
            ValueError: If the data is not int, list, or bytearray.
        """

        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, list):
            data_all = data
        elif isinstance(data, int):
            data_all = []
            if data == 0:
                data_all = [0]
            else:
                while data > 0:
                    data_all.append(data & 0xFF)
                    data >>= 8
        else:
            msg = "memory write requires argument of bytearray, list, or int"
            self.logger.error(msg)
            raise ValueError(msg)

        reg_description = get_address_description(memaddr)
        data_descriptions = [get_value_description(d) for d in data_all]
        self.logger.debug(
            f"mem_write: register [0x{memaddr:02X}] {reg_description} data {[f'0x{i:02X} {descr}' for i, descr in zip(data_all, data_descriptions)]}"
        )
        self._write_i2c_block_data(memaddr, data_all)

    def mem_read(self, length: int, memaddr: int) -> Optional[List[int]]:
        """
        Read data from a specific register address.

        Args:
            length (int): Number of bytes to receive.
            memaddr (int): Register address.

        Returns:
            list: List of bytes read from the register, or None if error.
        """

        result = self._read_i2c_block_data(memaddr, length)
        reg_description = get_address_description(memaddr)
        result_descriptions = [get_value_description(r) for r in result]
        self.logger.debug(
            f"mem_read: register [0x{memaddr:02X}] {reg_description} data {[f'0x{i:02X} {descr}' for i, descr in zip(result, result_descriptions)]}"
        )
        return result

    def is_avaliable(self) -> bool:
        """
        Check if the I2C device is available.

        Returns:
            bool: True if the I2C device is available, False otherwise.
        """

        return self.address in self.scan()
