from typing import Dict, Optional, Union

from app.util.logger import Logger


class MockGPIO(Logger):
    def __init__(self, pin, mode=None, pull=None):
        super().__init__(name=__name__)
        self.pin = pin
        self.mode = mode
        self.pull = pull
        self.value = 0

    def on(self):
        self.value = 1
        self.logger.info(f"[MOCK] GPIO{self.pin} set to HIGH")

    def off(self):
        self.value = 0
        self.logger.info(f"[MOCK] GPIO{self.pin} set to LOW")

    def close(self):
        print(f"[MOCK] GPIO{self.pin} closed")
        self.logger.info(f"[MOCK] GPIO{self.pin} closed")


class Pin(Logger):
    """Pin manipulation class"""

    OUT = 0x01
    """Pin mode output"""
    IN = 0x02
    """Pin mode input"""

    PULL_UP = 0x11
    """Pin internal pull up"""
    PULL_DOWN = 0x12
    """Pin internal pull down"""
    PULL_NONE = None
    """Pin internal pull none"""

    IRQ_FALLING = 0x21
    """Pin interrupt falling"""
    IRQ_RISING = 0x22
    """Pin interrupt rising"""
    IRQ_RISING_FALLING = 0x23
    """Pin interrupt both rising and falling"""

    _dict = {
        "D0": 17,
        "D1": 4,
        "D2": 27,
        "D3": 22,
        "D4": 23,
        "D5": 24,
        "D6": 25,
        "D7": 4,
        "D8": 5,
        "D9": 6,
        "D10": 12,
        "D11": 13,
        "D12": 19,
        "D13": 16,
        "D14": 26,
        "D15": 20,
        "D16": 21,
        "SW": 25,
        "USER": 25,
        "LED": 26,
        "BOARD_TYPE": 12,
        "RST": 16,
        "BLEINT": 13,
        "BLERST": 20,
        "MCURST": 5,
        "CE": 8,
    }

    def __init__(
        self,
        pin: Union[int, str],
        mode: Optional[int] = None,
        pull: Optional[int] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize a pin

        :param pin: pin number of Raspberry Pi
        :type pin: int/str
        :param mode: pin mode(IN/OUT)
        :type mode: int
        :param pull: pin pull up/down(PUD_UP/PUD_DOWN/PUD_NONE)
        :type pull: int
        """
        super().__init__(name=__name__, *args, **kwargs)

        # parse pin
        pin_dict = self.dict()
        if isinstance(pin, str):
            if pin not in pin_dict.keys():
                raise ValueError(f'Pin should be in {pin_dict.keys()}, not "{pin}"')
            self._board_name = pin
            self._pin_num = pin_dict[pin]
        elif isinstance(pin, int):
            if pin not in pin_dict.values():
                raise ValueError(f'Pin should be in {pin_dict.values()}, not "{pin}"')
            self._board_name = {i for i in pin_dict if pin_dict[i] == pin}
            self._pin_num = pin
        else:
            raise ValueError(f'Pin should be in {pin_dict.keys()}, not "{pin}"')
        # setup
        self._value = 0
        self.gpio = None
        self.setup(mode, pull)
        self.logger.info("Pin init finished.")

    def dict(self, _dict: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """
        Set/get the pin dictionary

        :param _dict: pin dictionary, leave it empty to get the dictionary
        :type _dict: dict
        :return: pin dictionary
        :rtype: dict
        """
        if _dict is None:
            return self._dict
        else:
            if not isinstance(_dict, dict):
                raise ValueError(
                    f'Argument should be a pin dictionary like {{"my pin": ezblock.Pin.cpu.GPIO17}}, not {_dict}'
                )
            self._dict = _dict
        return self._dict

    def close(self):
        if self.gpio:
            self.gpio.close()

    def deinit(self):
        if self.gpio:
            self.gpio.close()
            self.gpio = None

    def setup(self, mode, pull=None):
        """
        Setup the pin

        :param mode: pin mode(IN/OUT)
        :type mode: int
        :param pull: pin pull up/down(PUD_UP/PUD_DOWN/PUD_NONE)
        :type pull: int
        """
        if mode in [None, self.OUT, self.IN]:
            self._mode = mode
        else:
            raise ValueError(f"mode param error, should be None, Pin.OUT, Pin.IN")

        if pull in [self.PULL_NONE, self.PULL_DOWN, self.PULL_UP]:
            self._pull = pull
        else:
            raise ValueError(
                f"pull param error, should be None, Pin.PULL_NONE, Pin.PULL_DOWN, Pin.PULL_UP"
            )

        if self.gpio is not None:
            self.gpio.close()

        self.gpio = MockGPIO(self._pin_num, mode, pull)

    def __call__(self, value):
        return self.value(value)

    def value(self, value: Optional[int] = None):
        if value is None:
            if self._mode in [None, self.OUT]:
                self.setup(self.IN)
            result = self.gpio.value if self.gpio else None
            self.logger.debug(
                f"read pin {self.gpio.pin if self.gpio else None}: {result}"
            )
            return result
        else:
            if self._mode in [self.IN]:
                self.setup(self.OUT)
            res = 0
            if bool(value):
                res = 1
                if self.gpio is not None:
                    self.gpio.on()
            else:
                if self.gpio is not None:
                    self.gpio.off()
            return res

    def on(self):
        return self.value(1)

    def off(self):
        return self.value(0)

    def high(self):
        return self.on()

    def low(self):
        return self.off()

    def irq(self, handler, trigger, bouncetime=200, pull=None):
        self.logger.debug(
            f"read pin {handler}: trigger {trigger} bouncetime {bouncetime} pull {pull}"
        )

    def name(self):
        return f"GPIO{self._pin_num}"
