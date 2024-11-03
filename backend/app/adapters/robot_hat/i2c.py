"""
A module to manage communication between a Raspberry Pi and devices that support the I2C protocol.

I2C stands for Inter-Integrated Circuit and is a type of synchronous
communication protocol, that allows multiple integrated circuits (ICs) to
communicate with one another using just two lines:

- **SCL (Clock line)**: Synchronizes the data transfer between the devices.
- **SDA (Data line)**: Carries the data between the devices.

#### How They Work
- **Master**: The device that initiates and controls the communication.
- **Slave**: The device that responds to the master's request.
- Each I2C device has a unique address that allows the master to communicate with specific devices.
"""

import errno
from typing import Any, List, Optional, Union

from app.adapters.robot_hat.address_descriptions import (
    get_address_description,
    get_value_description,
)
from app.config.platform import is_os_raspberry
from app.util.logger import Logger

if is_os_raspberry:
    from smbus2 import SMBus
else:
    from app.adapters.robot_hat.mock.smbus2 import MockSMBus as SMBus


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
    I2C (Inter-Integrated Circuit) is a communication protocol that allows
    multiple integrated circuits (ICs) to communicate with one another using
    just two lines:
    - **SCL (Clock line)**: Synchronizes the data transfer between the devices.
    - **SDA (Data line)**: Carries the data between the devices.

    #### How They Work
    - **Master**: The device that initiates and controls the communication.
    - **Slave**: The device that responds to the master's request.
    - Each I2C device has a unique address that allows the master to communicate with specific devices.

    #### Playing with I2C
    Imagine you have several sensors and devices connected to your Raspberry Pi
    using I2C. You can easily read and write data to them using the I2C class.
    For example, you can:
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
        self.logger.debug(
            "Writing a single byte to the I2C address %s Data: [0x%02X] %s",
            self.address,
            data,
            description,
        )
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
        if self.address:
            reg_description = get_address_description(reg)
            data_description = get_value_description(data)
            self.logger.debug(
                "Writing a byte of data on I2C address %s Register: [0x%02X] %s Data: [0x%02X] %s",
                hex(self.address),
                reg,
                reg_description,
                data,
                data_description,
            )
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

        if self.address:
            reg_description = get_address_description(reg)
            data_description = get_value_description(data)
            self.logger.debug(
                "Writing a single word (2 bytes) on I2C address %s Register: [0x%02X] %s Data: [0x%04X] %s",
                hex(self.address),
                reg,
                reg_description,
                data,
                data_description,
            )
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

        if self.address:
            reg_description = get_address_description(reg)
            data_descriptions = [get_value_description(d) for d in data]
            self.logger.debug(
                "Writing blocks of data on I2C address %s Register: [0x%02X] %s Data: %s",
                hex(self.address),
                reg,
                reg_description,
                [f"0x{i:02X} {descr}" for i, descr in zip(data, data_descriptions)],
            )
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
            self.logger.debug(
                "Read a single byte on the I2C address %s Result: [0x%02X] %s",
                hex(self.address),
                result,
                description,
            )
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
                "Read a byte of data: [0x%02X] %s [0x%02X] %s",
                reg,
                reg_description,
                result,
                result_description,
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
                "Read a word of data on the I2C address %s Register: [0x%02X] %s Result: [0x%04X] %s",
                self.address,
                reg,
                reg_description,
                result,
                result_description,
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
                "Read blocks of data on the I2C address %s from a register [0x%02X] %s Result: %s",
                self.address,
                reg,
                reg_description,
                [f"0x{i:02X} {descr}" for i, descr in zip(result, result_descriptions)],
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
        Scan the I2C bus for devices using smbus2.

        Returns:
            List[int]: List of I2C addresses of devices found.
        """
        addresses = []
        self.logger.debug(f"Scanning I2C bus {self._bus} for devices")

        for address in range(
            0x03, 0x78
        ):  # Most valid addresses fall between 0x03 and 0x77
            try:
                self._smbus.write_byte(
                    address, 0
                )  # Attempt to write a dummy byte to the address
                addresses.append(address)
                self.logger.debug("Found I2C device at 0x%02x", address)
            except OSError as e:
                # Ignore devices that don't acknowledge (errno corresponds to "No such device or address")
                if e.errno != errno.EREMOTEIO:
                    self.logger.debug(f"OSError at I2C address 0x{address:02x}: {e}")
                continue
            except Exception as e:
                self.logger.error(
                    "Unexpected error at I2C address 0x%02x: %s", address, e
                )
                continue

        self.logger.debug(
            "Connected I2C devices: %s", ['0x%02x' % addr for addr in addresses]
        )
        return addresses

    def write(self, data: Union[int, List[int], bytearray]) -> None:
        """
        Write data to the I2C device, with support for various data formats.

        This method delivers data over the I2C bus to the connected device. It is flexible in that
        it accepts an integer, a list of integers, or a bytearray. Based on the size of the
        provided data, this function internally delegates to the appropriate low-level I2C
        transmission method (_write_byte, _write_byte_data, _write_word_data, or _write_i2c_block_data).

        Data Interpretation Based on Input:
            - **Integer (int)**:
                - If it's a single byte (e.g., `0x00` to `0xFF`), it will be sent as a single byte.
                - If it's a multi-byte integer, it will be broken into 8-bit segments and transmitted as appropriate.
            - **List of integers (List[int])**: Interpreted as an array of sequential bytes. Depending on the length of the list:
                - 1 byte: Written as a single byte.
                - 2 bytes: The first byte is the register, and the second is the data byte.
                - 3+ bytes: The first byte is the register, and the remaining are sent as block data.
            - **Bytearray (bytearray)**: Treated as a list of bytes. The bytearray is converted to a list before transmission.

        Args:
            data (Union[int, list, bytearray]): Input data to write. This can be:
                - An integer, which is either a single byte or a sequence of bytes.
                - A list of integers, where each integer represents a byte.
                - A bytearray, which is treated similarly to a list of bytes.

        Raises:
            ValueError: If the data cannot be processed as an integer, list, or bytearray.

        I2C Handling Logic:
            - If the data length is 1: Write a single byte using `_write_byte`.
            - If the data length is 2: Write a register and a corresponding byte using `_write_byte_data`.
            - If the data length is 3: Write a register and a 16-bit word (2 bytes) using `_write_word_data`.
            - If the data is 4 bytes or more: Write a block of data using `_write_i2c_block_data`.

        Example:
            For a register `0x10`, writing the value `0xABCD` could be done through:

            ```python
            self.write([0x10, 0xCD, 0xAB])  # Calls _write_word_data with reg=0x10, data=0xABCD
            ```

        Returns:
            None
        """

        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, int):
            # Convert integer (could be multi-byte) input into a list of bytes, lowest first
            if data == 0:
                data_all = [0]
            else:
                data_all = []
                while data > 0:
                    data_all.append(data & 0xFF)  # Append the least significant byte
                    data >>= 8  # Shift right to prepare for the next byte
        elif isinstance(data, list):
            data_all = data

        data_len = len(data_all)

        if data_len == 1:
            data = data_all[0]
            self._write_byte(data)
        elif data_len == 2:
            # Two-byte write where first item is register, second item is the value
            reg = data_all[0]
            data = data_all[1]
            self._write_byte_data(reg, data)
        elif data_len == 3:
            # Three-byte write: first byte is the register, next two bytes form a 16-bit word
            reg = data_all[0]
            data = (data_all[2] << 8) + data_all[1]
            self._write_word_data(reg, data)
        else:
            # For more than 3 bytes: block write (first byte is the register, rest is data)
            reg = data_all[0]
            data = list(
                data_all[1:]
            )  # All bytes after the first are written as block data
            self._write_i2c_block_data(reg, data)

    def read(self, length: int = 1):
        """
        Read a specified number of bytes from the I2C device.

        This method reads data from the I2C device using the `_read_byte()` method,
        which retrieves one byte at a time. The number of bytes to read is determined
        by the `length` parameter. The method accumulates these bytes into a list and
        returns them. If a read operation fails (i.e., returns `None`), a warning
        message is logged, but the method will continue reading subsequent bytes.

        Args:
            length (int): The number of bytes to read from the I2C device. Defaults to 1.
                          The length must be a positive integer.

        Returns:
            list: A list containing `length` bytes read from the device. If any read
                  operation fails and returns `None`, the list may have fewer bytes
                  than requested or exclude erroneous values.

        Raises:
            ValueError: If `length` is non-positive or invalid.

        Operation Details:
            - The method reads one byte at a time by calling the internal `_read_byte()` function.
            - In the event that `_read_byte()` returns `None`, this indicates a failure to read
              a byte from the device. In such cases, a warning is logged, showing how many bytes
              successfully read before encountering the issue.
            - The overall process continues even if one or more failures occur, and the result
              returns the bytes that were successfully read.

        Logging:
            - If the read operation fails for any byte (i.e., `_read_byte()` returns `None`),
              the method logs a warning like:
              `Read {i} byte of ({length}) from the I2C address {self.address} is None`

        Example:
            ```python
            data = self.read(3)  # Reads 3 bytes from the I2C device
            print(data)          # Output: [0x01, 0xA9, 0x34] (example bytes)
            ```

        Note:
            Some implementations of `_read_byte()` might return `None` in case of hardware
            communication errors or timeouts. Therefore, you should be prepared to handle
            incomplete results.
        """

        result = []
        for i in range(length):
            byte = self._read_byte()
            if byte is not None:
                result.append(byte)
            else:
                self.logger.warning(
                    "Read %s byte of (%s) from the I2C address %s is None",
                    i,
                    length,
                    self.address,
                )
        return result

    def mem_write(self, data: Union[int, List[int], bytearray], memaddr: int) -> None:
        """
        Write data to a specific memory address (register) on the I2C device.

        This method allows writing data directly to a specific memory address, such as a register
        within the I2C device. The memory address (`memaddr`) determines where the data should
        be stored on the device. The function supports multiple input data types (int, list of
        integers, or bytearray) and converts these inputs into a sequence of bytes to be transferred.

        Args:
            data (Union[int, list, bytearray]): The data to write. This can be:
                - A single integer: It can represent one or more bytes (0xFFFF is 2 bytes: [0xFF, 0xFF]).
                - A list of integers: Each integer represents a byte (e.g., `[0x12, 0x34]`).
                - A bytearray: Treated similarly to a list of bytes.

            memaddr (int): The register (memory address) of the device where the data will be written.

        Raises:
            ValueError: If the data is not an integer, list of integers, or bytearray.

        Processing the Input Data:
            - **Integers**: If the input is an integer, it is split into individual bytes
              before being sent. For example, the integer `0x1234` will be split into
              two bytes `[0x12, 0x34]` and transmitted separately.
            - **Lists and Bytearrays**: These are treated as sequences of bytes and directly
              passed on for transmission.

        Transfer Details:
            The data is written to the specified `memaddr` register using the internal method
            `_write_i2c_block_data()`.

        Example:
            To write `0x1234` to register `0x10`:
            ```python
            self.mem_write(0x1234, 0x10)
            # Transmits [0x10] register and [0x12, 0x34] as the 16-bit data
            ```

        Returns:
            None
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
                    data_all.append(data & 0xFF)  # Append the least significant byte
                    data >>= 8  # Shift right to prepare for the next byte
        self._write_i2c_block_data(memaddr, data_all)

    def mem_read(self, length: int, memaddr: int) -> Optional[List[int]]:
        """
        Read data from a specific memory address (register) on the I2C device.

        This method reads a specified number of bytes from a given memory address (register)
        on the I2C device. The address `memaddr` is an internal register or memory location
        on the device from which `length` bytes will be fetched. The method will log any errors
        encountered during the read operation.

        Args:
            length (int): The number of bytes to read from the specified memory address.
            memaddr (int): The register (address) from which to read data.

        Returns:
            Optional[List[int]]: Returns a list of bytes read from the register. If an error occurs,
                                 this method will log an error and return `None`.

        Transfer Details:
            - The method reads `length` bytes starting from `memaddr` using the internal
              `_read_i2c_block_data()` method, which interacts with the underlying I2C
              communication system.
            - If the read is successful, it will store the data in a list and return it.
              Otherwise, it will log an error message if the read fails and return `None`.

        Logging:
            On a successful read, the result is logged along with descriptions for the
            memory and value. For example:
            ```plaintext
            Read data from I2C address 0x50, Register [0x10]: Result: [0x12 'desc1', 0x34 'desc2']
            ```

            If a read fails, an error message is logged:
            ```plaintext
            Failed to read data from I2C address 0x50, Register [0x10]
            ```

        Example:
            To read 4 bytes from register `0x10`:
            ```python
            data = self.mem_read(4, 0x10)
            # Example output: [0x12, 0x34, 0x56, 0x78]
            ```

        Returns:
            Optional[List[int]]: A list of bytes read from the specified register, or `None` if an error occurs.
        """

        result = self._read_i2c_block_data(memaddr, length)
        reg_description = get_address_description(memaddr)
        if result is None:
            self.logger.error(
                "Failed to read data from I2C address %s, register [0x%02X] %s",
                self.address,
                memaddr,
                reg_description,
            )
        else:
            result_descriptions = [get_value_description(r) for r in result]
            self.logger.debug(
                "Read data from I2C address %s, Register [0x%02X] %s Result: %s",
                self.address,
                memaddr,
                reg_description,
                [f'0x{i:02X} {descr}' for i, descr in zip(result, result_descriptions)],
            )

        return result

    def is_avaliable(self) -> bool:
        """
        Check if the I2C device is available.

        Returns:
            bool: True if the I2C device is available, False otherwise.
        """

        return self.address in self.scan()
