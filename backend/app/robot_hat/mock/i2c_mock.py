import random
from app.robot_hat.basic import Basic_class


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
                self._debug(f"OSError: {func.__name__}")
                continue
        else:
            return False

    return wrapper


class I2C(Basic_class):
    RETRY = 5

    def __init__(self, address=None, bus=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self._debug(f"_write_byte: [0x{data:02X}]")
        return 0  # Simulate successful write

    @_retry_wrapper
    def _write_byte_data(self, reg, data):
        self._debug(f"_write_byte_data: [0x{reg:02X}] [0x{data:02X}]")
        return 0  # Simulate successful write

    @_retry_wrapper
    def _write_word_data(self, reg, data):
        self._debug(f"_write_word_data: [0x{reg:02X}] [0x{data:04X}]")
        return 0  # Simulate successful write

    @_retry_wrapper
    def _write_i2c_block_data(self, reg, data):
        self._debug(
            f"_write_i2c_block_data: [0x{reg:02X}] {[f'0x{i:02X}' for i in data]}"
        )
        return 0  # Simulate successful write

    @_retry_wrapper
    def _read_byte(self):
        result = random.randint(0, 255)  # Simulate a random byte read
        self._debug(f"_read_byte: [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_byte_data(self, reg):
        result = random.randint(0, 255)  # Simulate a random byte read
        self._debug(f"_read_byte_data: [0x{reg:02X}] [0x{result:02X}]")
        return result

    @_retry_wrapper
    def _read_word_data(self, reg):
        result = random.randint(0, 65535)  # Simulate a random word read
        result_list = [result & 0xFF, (result >> 8) & 0xFF]
        self._debug(f"_read_word_data: [0x{reg:02X}] [0x{result:04X}]")
        return result_list

    @_retry_wrapper
    def _read_i2c_block_data(self, reg, num):
        result = [random.randint(0, 255) for _ in range(num)]  # Simulate a block read
        self._debug(
            f"_read_i2c_block_data: [0x{reg:02X}] {[f'0x{i:02X}' for i in result]}"
        )
        return result

    @_retry_wrapper
    def is_ready(self):
        addresses = self.scan()
        return self.address in addresses

    def scan(self):
        return []

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
        self._write_i2c_block_data(memaddr, data_all)

    def mem_read(self, length, memaddr):
        result = self._read_i2c_block_data(memaddr, length)
        return result

    def is_avaliable(self):
        return self.address in self.scan()


if __name__ == "__main__":
    i2c = I2C(address=[0x17, 0x15], debug_level="debug")
