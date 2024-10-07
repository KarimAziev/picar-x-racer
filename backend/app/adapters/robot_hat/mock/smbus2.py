class MockSMBus:
    def __init__(self, bus=None, force=False):
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

    def open(self, bus):
        self.fd = 1
        self.bus = bus

    def close(self):
        self.fd = None

    def _set_address(self, address, force=None):
        self.address = address
        self._force_last = force or self.force

    def write_quick(self, i2c_addr, force=None):
        self._set_address(i2c_addr, force)
        return

    def read_byte(self, i2c_addr, force=None):
        self._set_address(i2c_addr, force)
        return self._command_responses["byte"]

    def write_byte(self, i2c_addr, value, force=None):
        self._set_address(i2c_addr, force)
        return

    def read_byte_data(self, i2c_addr, register, force=None):
        self._set_address(i2c_addr, force)
        return self._command_responses["byte"]

    def write_byte_data(self, i2c_addr, register, value, force=None):
        self._set_address(i2c_addr, force)
        return

    def read_word_data(self, i2c_addr, register, force=None):
        self._set_address(i2c_addr, force)
        return self._command_responses["word"]

    def write_word_data(self, i2c_addr, register, value, force=None):
        self._set_address(i2c_addr, force)
        return

    def process_call(self, i2c_addr, register, value, force=None):
        self._set_address(i2c_addr, force)
        return self._command_responses["word"]

    def read_block_data(self, i2c_addr, register, force=None):
        self._set_address(i2c_addr, force)
        return self._command_responses["block"]

    def write_block_data(self, i2c_addr, register, data, force=None):
        self._set_address(i2c_addr, force)
        return

    def block_process_call(self, i2c_addr, register, data, force=None):
        self._set_address(i2c_addr, force)
        return self._command_responses["block"]

    def write_i2c_block_data(self, i2c_addr, register, data, force=None):
        self._set_address(i2c_addr, force)
        return

    def read_i2c_block_data(self, i2c_addr, register, length, force=None):
        self._set_address(i2c_addr, force)
        return self._command_responses["block"][:length]

    def i2c_rdwr(self, *i2c_msgs):
        return

    def enable_pec(self, enable=True):
        self.pec = int(enable)  # Simulate enabling PEC


if __name__ == "__main__":
    mock_bus = MockSMBus(1)
    mock_bus.open(1)

    print("Read byte:", mock_bus.read_byte(0x10))
    print("Read word:", mock_bus.read_word_data(0x10, 0x01))
    print("Read block:", mock_bus.read_block_data(0x10, 0x01))

    mock_bus.close()
