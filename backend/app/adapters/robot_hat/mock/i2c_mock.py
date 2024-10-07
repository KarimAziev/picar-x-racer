import random

from app.adapters.robot_hat.address_descriptions import (
    get_address_description,
    get_value_description,
)
from app.util.logger import Logger


# Mocking command runner for i2cdetect simulation
def run_command(_):
    # Simulate the output of 'i2cdetect' command
    i2cdetect_output = """
     0 1 2 3 4 5 6 7 8 9 a b c d e f
00:          -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- 15 -- -- 17
    """
    return 0, i2cdetect_output


def _retry_wrapper(func):
    def wrapper(self, *args, **kwargs):
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
    RETRY = 5

    def __init__(self, address=None, bus=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = Logger(name=__name__)
        self._bus = bus
        self._smbus = None  # We don't have actual smbus, it's simulated.
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
    def _write_byte(self, data):
        description = get_value_description(data)
        self.logger.debug(f"_write_byte: [0x{data:02X}] {description}")
        return 0  # Simulate successful write

    @_retry_wrapper
    def _write_byte_data(self, reg, data):
        reg_description = get_address_description(reg)
        data_description = get_value_description(data)
        self.logger.debug(
            f"_write_byte_data: [0x{reg:02X}] {reg_description} [0x{data:02X}] {data_description}"
        )
        return 0  # Simulate successful write

    @_retry_wrapper
    def _write_word_data(self, reg, data):
        reg_description = get_address_description(reg)
        data_description = get_value_description(data)
        self.logger.debug(
            f"_write_word_data: [0x{reg:02X}] {reg_description} [0x{data:04X}] {data_description}"
        )
        return 0  # Simulate successful write

    @_retry_wrapper
    def _write_i2c_block_data(self, reg, data):
        reg_description = get_address_description(reg)
        data_descriptions = [get_value_description(d) for d in data]
        self.logger.debug(
            f"_write_i2c_block_data: [0x{reg:02X}] {reg_description} {[f'0x{i:02X} {descr}' for i, descr in zip(data, data_descriptions)]}"
        )
        return 0  # Simulate successful write

    @_retry_wrapper
    def _read_byte(self):
        result = random.randint(0, 255)  # Simulate a random byte read
        self.logger.debug(f"_read_byte: [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_byte_data(self, reg):
        result = random.randint(0, 255)  # Simulate a random byte read
        reg_description = get_address_description(reg)
        result_description = get_value_description(result)
        self.logger.debug(
            f"_read_byte_data: [0x{reg:02X}] {reg_description} [0x{result:02X}] {result_description}"
        )

        return result

    @_retry_wrapper
    def _read_word_data(self, reg):
        result = random.randint(0, 65535)  # Simulate a random word read
        result_list = [result & 0xFF, (result >> 8) & 0xFF]
        reg_description = get_address_description(reg)
        result_description = get_value_description(result)
        self.logger.debug(
            f"_read_word_data: [0x{reg:02X}] {reg_description} [0x{result:04X}] {result_description}"
        )
        return result_list

    @_retry_wrapper
    def _read_i2c_block_data(self, reg, num):
        result = [random.randint(0, 255) for _ in range(num)]  # Simulate a block read
        reg_description = get_address_description(reg)
        result_descriptions = [get_value_description(r) for r in result]
        self.logger.debug(
            f"_read_i2c_block_data: [0x{reg:02X}] {reg_description} {[f'0x{i:02X} {descr}' for i, descr in zip(result, result_descriptions)]}"
        )

        return result

    @_retry_wrapper
    def is_ready(self):
        addresses = self.scan()
        return self.address in addresses

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
                self.logger.debug(f"Found device at 0x{address:02x}")
            except OSError as e:
                # Ignore devices that don't acknowledge (errno corresponds to "No such device or address")
                if e.errno != errno.EREMOTEIO:
                    self.logger.debug(f"OSError at address 0x{address:02x}: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error at address 0x{address:02x}: {e}")
                continue

    def write(self, data):
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
            raise ValueError(
                f"write data must be int, list, or bytearray, not {type(data)}"
            )

        if len(data_all) == 1:
            data = data_all[0]
            self._write_byte(data)
        elif len(data_all) == 2:
            reg = data_all[0]
            data = data_all[1]
            self._write_byte_data(reg, data)
        elif len(data_all) == 3:
            reg = data_all[0]
            data = (data_all[2] << 8) + data_all[1]
            self._write_word_data(reg, data)
        else:
            reg = data_all[0]
            data = list(data_all[1:])
            self._write_i2c_block_data(reg, data)

    def read(self, length=1):
        if not isinstance(length, int):
            raise ValueError(f"length must be int, not {type(length)}")
        result = []
        for _ in range(length):
            result.append(self._read_byte())
        return result

    def mem_write(self, data, memaddr):
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
            raise ValueError(
                "memery write require arguement of bytearray, list, int less than 0xFF"
            )
        reg_description = get_address_description(memaddr)
        data_descriptions = [get_value_description(d) for d in data_all]
        self.logger.debug(
            f"mem_write: register [0x{memaddr:02X}] {reg_description} data {[f'0x{i:02X} {descr}' for i, descr in zip(data_all, data_descriptions)]}"
        )
        self._write_i2c_block_data(memaddr, data_all)

    def mem_read(self, length, memaddr):
        result = self._read_i2c_block_data(memaddr, length)
        reg_description = get_address_description(memaddr)
        result_descriptions = [get_value_description(r) for r in result]
        self.logger.debug(
            f"mem_read: register [0x{memaddr:02X}] {reg_description} data {[f'0x{i:02X} {descr}' for i, descr in zip(result, result_descriptions)]}"
        )
        return result

    def is_avaliable(self):
        return self.address in self.scan()


if __name__ == "__main__":
    i2c = I2C(address=[0x17, 0x15], debug_level="debug")
