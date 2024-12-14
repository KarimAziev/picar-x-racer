import errno
from typing import List, Optional, Sequence, Union

from app.util.logger import Logger

from smbus2 import i2c_msg

logger = Logger(__name__)


class MockSMBus:
    def __init__(self, bus: Union[None, int, str], force: bool = False):
        self.bus = bus
        self.force = force
        self.fd = None
        self.pec = 0
        self.address = None
        self._force_last = None

        self._command_responses = {
            "byte": 0x12,
            "word": 0x1234,
            "block": [1, 2, 3, 4, 5],
        }

    def open(self, bus: Union[int, str]) -> None:
        self.fd = 1
        self.bus = bus

    def close(self) -> None:
        self.fd = None

    def _set_address(self, address: int, force: Optional[bool] = None):
        self.address = address
        self._force_last = force or self.force

    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None:
        self._set_address(i2c_addr, force)
        return

    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int:
        self._set_address(i2c_addr, force)
        return self._command_responses["byte"]

    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_byte: %s", value)
        if i2c_addr != 20:
            raise OSError(errno.EREMOTEIO, "No such device or address")
        self._set_address(i2c_addr, force)
        return

    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        logger.debug("read_byte_data: %s", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["byte"]

    def write_byte_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_byte_data '%s' to '%s'", register, value)
        self._set_address(i2c_addr, force)
        return

    def read_word_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        logger.debug("read_word_data from register '%s'", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["word"]

    def write_word_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_word_data %s to register '%s'", value, register)
        self._set_address(i2c_addr, force)
        return

    def process_call(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ):
        logger.debug("write_word_data %s to register '%s'", value, register)
        self._set_address(i2c_addr, force)
        return self._command_responses["word"]

    def read_block_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> List[int]:
        logger.debug("read_block_data register '%s'", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["block"]

    def write_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        logger.debug("write_block_data %s to register '%s'", data, register)
        self._set_address(i2c_addr, force)
        return

    def block_process_call(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ):
        logger.debug("block_process_call %s to register '%s'", data, register)
        self._set_address(i2c_addr, force)
        return self._command_responses["block"]

    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ):
        logger.debug("write_i2c_block_data %s to register '%s'", data, register)
        self._set_address(i2c_addr, force)
        return

    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]:
        logger.debug("read_i2c_block_data register: %s", register)
        self._set_address(i2c_addr, force)
        return self._command_responses["block"][:length]

    def i2c_rdwr(self, *i2c_msgs: i2c_msg) -> None:
        logger.debug("%s", i2c_msgs)
        return

    def enable_pec(self, enable=True) -> None:
        self.pec = int(enable)  # Simulate enabling PEC


if __name__ == "__main__":
    mock_bus = MockSMBus(1)
    mock_bus.open(1)

    print("Read byte:", mock_bus.read_byte(0x10))
    print("Read word:", mock_bus.read_word_data(0x10, 0x01))
    print("Read block:", mock_bus.read_block_data(0x10, 0x01))

    mock_bus.close()
