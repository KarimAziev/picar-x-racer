"""
A module to manage the pins of a Raspberry Pi and perform various operations like:
- setting up pin modes
- reading or writing values to the pin
- configuring interrupts.

#### What Are Pins?
Pins are tiny metal sticks or connectors on the board that can be used for different purposes like sending signals (messages), powering up things, sensing things, and more.

#### Types of Pins
1. **Power Pins**: These are like magic sources that give energy to other parts. They are usually labeled as **3.3V** or **5V** (the amount of energy they provide).
2. **Ground Pins (GND)**: These are like the ground in your house. They help to complete the electrical circuit safely.
3. **GPIO Pins (General-Purpose Input/Output)**: Think of these as the magic wands. They can be used for either sending out signals (Output) or receiving signals (Input).

#### How They Work
- **Power Pins**: If you connect a toy that needs power to these pins, it will turn on!
- **Ground Pins**: When you connect your toys to these, it helps to complete the magic circuit, making everything safe and working.
- **GPIO Pins**: You can turn lights on and off, read switches, control motors, and do many other magical things by connecting these.
"""

from typing import Dict, Optional, Union

from app.util.logger import Logger
from gpiozero import Button, InputDevice, OutputDevice


class Pin(object):
    """
    A class to manage the pins of a Raspberry Pi and perform various operations like setting up pin modes, reading or writing values to the pin, and configuring interrupts.

    ### Pin Modes:
    - OUT (0x01): Configure the pin as an output pin.
    - IN (0x02): Configure the pin as an input pin.

    ### Internal Pull-Up/Pull-Down Resistors:
    - PULL_UP (0x11): Enable internal pull-up resistor.
    - PULL_DOWN (0x12): Enable internal pull-down resistor.
    - PULL_NONE (None): No internal pull-up or pull-down resistor.

    ### Interrupt Triggers:
    - IRQ_FALLING (0x21): Interrupt on falling edge.
    - IRQ_RISING (0x22): Interrupt on rising edge.
    - IRQ_RISING_FALLING (0x23): Interrupt on both rising and falling edges.

    ### Attributes:
        - `_dict` (Dict[str, int]): Dictionary to map board names to GPIO pin numbers.

    ### Methods:
        - `__init__(self, pin: Union[int, str], mode: Optional[int] = None, pull: Optional[int] = None)`: Initialize the Pin.
        - `dict(self, _dict: Optional[Dict[str, int]] = None) -> Dict[str, int]`: Set/get the pin dictionary.
        - `close(self)`: Close the GPIO pin.
        - `deinit(self)`: Deinitialize the GPIO pin and its pin factory.
        - `setup(self, mode, pull=None)`: Set up the GPIO pin mode and pull-up/down resistors.
        - `__call__(self, value)`: Set/get the pin value.
        - `value(self, value: Optional[int] = None)`: Set/get the pin value.
        - `on(self)`: Set the pin value to high (1).
        - `off(self)`: Set the pin value to low (0).
        - `high(self)`: Alias for `on()`.
        - `low(self)`: Alias for `off()`.
        - `irq(self, handler, trigger, bouncetime=200, pull=None)`: Set the pin interrupt handler.
        - `name(self)`: Get the pin name.

    #### What Are Pins?
    Pins are tiny metal sticks or connectors on the board that can be used for different purposes like sending signals (messages), powering up things, sensing things, and more.

    #### Types of Pins
    1. **Power Pins**: These are like magic sources that give energy to other parts. They are usually labeled as **3.3V** or **5V** (the amount of energy they provide).
    2. **Ground Pins (GND)**: These are like the ground in your house. They help to complete the electrical circuit safely.
    3. **GPIO Pins (General-Purpose Input/Output)**: Think of these as the magic wands. They can be used for either sending out signals (Output) or receiving signals (Input).

    #### How They Work
    - **Power Pins**: If you connect a toy that needs power to these pins, it will turn on!
    - **Ground Pins**: When you connect your toys to these, it helps to complete the magic circuit, making everything safe and working.
    - **GPIO Pins**: You can turn lights on and off, read switches, control motors, and do many other magical things by connecting these.

    #### Playing with Pins
    Let's say you have an LED light, just like a small light bulb.
    1. You connect one leg of the LED light to a **3.3V Power Pin** (for energy).
    2. Connect the other leg to a **Ground Pin** (to complete the circuit).
    3. Now, if you want to control this light using code, you would connect the LED light to one of the **GPIO Pins**.

    By writing some code, you can tell the GPIO Pin to turn the light on or off.
    """

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
        "D1": 4,  # Changed
        "D2": 27,
        "D3": 22,
        "D4": 23,
        "D5": 24,
        "D6": 25,  # Removed
        "D7": 4,  # Removed
        "D8": 5,  # Removed
        "D9": 6,
        "D10": 12,
        "D11": 13,
        "D12": 19,
        "D13": 16,
        "D14": 26,
        "D15": 20,
        "D16": 21,
        "SW": 25,  # Changed
        "USER": 25,
        "LED": 26,
        "BOARD_TYPE": 12,
        "RST": 16,
        "BLEINT": 13,
        "BLERST": 20,
        "MCURST": 5,  # Changed
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
        Initialize a GPIO Pin.

        Args:
            pin (Union[int, str]): Pin number or name of the Raspberry Pi.
            mode (Optional[int]): Mode of the pin, either `Pin.OUT` for output or `Pin.IN` for input. Default is None.
            pull (Optional[int]): Configure internal pull-up or pull-down resistors. `Pin.PULL_UP`, `Pin.PULL_DOWN`, or `Pin.PULL_NONE`. Default is None.

        Raises:
            ValueError: If the provided pin is not in the pin dictionary or not a valid type.
        """
        super().__init__(*args, **kwargs)
        self.logger = Logger(__name__)

        # Parse pin
        pin_dict = self.dict()
        if isinstance(pin, str):
            if pin not in pin_dict.keys():
                msg = f'Pin should be in {self._dict.keys()}, not "{pin}"'
                self.logger.error(msg)
                raise ValueError(msg)
            self._board_name = pin
            self._pin_num = pin_dict[pin]
        elif isinstance(pin, int):
            if pin not in pin_dict.values():
                msg = f'Pin should be in {pin_dict.values()}, not "{pin}"'
                self.logger.error(msg)
                raise ValueError(msg)
            self._board_name = {i for i in pin_dict if pin_dict[i] == pin}
            self._pin_num = pin
        else:
            msg = f'Pin should be in {pin_dict.keys()}, not "{pin}"'
            self.logger.error(msg)
            raise ValueError(msg)

        self._value = 0
        self.gpio = None
        self.setup(mode, pull)
        mode_str = (
            "NONE PIN"
            if mode is None
            else "OUT PIN" if mode == self.OUT else "INPUT PIN"
        )
        pull_str = (
            "No internal resistor"
            if pull is None
            else "PULL-UP resistor" if pull == self.PULL_UP else "PULL-DOWN resistor"
        )
        pull_hex = "None" if pull is None else f"0x{pull:02X}"
        self.logger.info(
            f"Initted {mode_str} {self._board_name} (0x{self._pin_num:02X}) with {pull_str} ({pull_hex})"
        )

    def dict(self, _dict: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        """
        Set or get the pin dictionary which maps pin names to GPIO numbers.

        Args:
            _dict (Optional[Dict[str, int]]): Provide a new pin dictionary. Leave it empty to get the current dictionary.

        Returns:
            Dict[str, int]: The current pin dictionary.

        Raises:
            ValueError: If the provided dictionary is not of valid format.
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
        """
        Close the GPIO pin.
        """
        if self.gpio:
            self.gpio.close()

    def deinit(self):
        """
        Deinitialize the GPIO pin and its factory.
        """
        if self.gpio:
            self.gpio.close()
            pin_factory = self.gpio.pin_factory
            if pin_factory is not None:
                pin_factory.close()

    def setup(self, mode, pull=None):
        """
        Setup the GPIO pin with a specific mode and optional pull-up/down resistor configuration.

        Args:
            mode (int): Mode of the pin (`Pin.OUT` for output, `Pin.IN` for input). Default is None.
            pull (Optional[int]): Configure pull-up/down resistors (`Pin.PULL_UP`, `Pin.PULL_DOWN`, `Pin.PULL_NONE`). Default is None.

        Raises:
            ValueError: If the mode or pull parameters are not valid.
        """
        if mode in [None, self.OUT, self.IN]:
            self._mode = mode
        else:
            msg = f"mode param error, should be None, Pin.OUT, Pin.IN"
            self.logger.error(msg)
            raise ValueError(msg)

        if pull in [self.PULL_NONE, self.PULL_DOWN, self.PULL_UP]:
            self._pull = pull
        else:
            msg = f"pull param error, should be None, Pin.PULL_NONE, Pin.PULL_DOWN, Pin.PULL_UP"
            self.logger.error(msg)
            raise ValueError(msg)

        if self.gpio != None:
            if self.gpio.pin != None:
                self.gpio.close()

        if mode in [None, self.OUT]:
            self.gpio = OutputDevice(self._pin_num)
        else:
            if pull in [self.PULL_UP]:
                self.gpio = InputDevice(self._pin_num, pull_up=True)
            else:
                self.gpio = InputDevice(self._pin_num, pull_up=False)

    def __call__(self, value):
        """
        Set or get the value of the GPIO pin.

        Args:
            value (int): Value to set the pin (high=1, low=0).

        Returns:
            int: Value of the pin (0 or 1).
        """
        return self.value(value)

    def value(self, value: Optional[int] = None):
        """
        Set or get the value of the GPIO pin.

        Args:
            value (Optional[int]): Value to set the pin (high=1, low=0). Leave empty to get the current value.

        Returns:
            int: Value of the pin (0 or 1) if value is not provided.

        Raises:
            ValueError: If the mode is not valid or the pin is not properly initialized.
        """
        if value == None:
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
            if bool(value):
                res = 1
                if isinstance(self.gpio, OutputDevice):
                    self.gpio.on()
            else:
                res = 0
                if isinstance(self.gpio, OutputDevice):
                    self.gpio.off()
            return res

    def on(self):
        """
        Set the pin value to high (1).

        Returns:
            int: The set pin value (1).
        """
        return self.value(1)

    def off(self):
        """
        Set the pin value to low (0).

        Returns:
            int: The set pin value (0).
        """
        return self.value(0)

    def high(self):
        """
        Alias for `on()` - Set the pin value to high (1).

        Returns:
            int: The set pin value (1).
        """
        return self.on()

    def low(self):
        """
        Alias for `off()` - Set the pin value to low (0).

        Returns:
            int: The set pin value (0).
        """
        return self.off()

    def irq(self, handler, trigger, bouncetime=200, pull=None):
        """
        Set the pin interrupt handler.

        Args:
            handler (function): Interrupt handler callback function.
            trigger (int): Interrupt trigger (`Pin.IRQ_FALLING`, `Pin.IRQ_RISING`, `Pin.IRQ_RISING_FALLING`).
            bouncetime (int): Interrupt debounce time in milliseconds. Default is 200.
            pull (Optional[int]): Configure pull-up/down resistors (`Pin.PULL_UP`, `Pin.PULL_DOWN`, `Pin.PULL_NONE`). Default is None.

        Raises:
            ValueError: If the trigger or pull parameters are not valid.
        """
        if trigger not in [self.IRQ_FALLING, self.IRQ_RISING, self.IRQ_RISING_FALLING]:
            raise ValueError(
                f"trigger param error, should be Pin.IRQ_FALLING, Pin.IRQ_RISING, Pin.IRQ_RISING_FALLING"
            )

        if pull in [self.PULL_NONE, self.PULL_DOWN, self.PULL_UP]:
            self._pull = pull
            if pull == self.PULL_UP:
                _pull_up = True
            else:
                _pull_up = False
        else:
            raise ValueError(
                f"pull param error, should be Pin.PULL_NONE, Pin.PULL_DOWN, Pin.PULL_UP"
            )

        pressed_handler = None
        released_handler = None

        if not isinstance(self.gpio, Button):
            if self.gpio != None:
                self.gpio.close()
            self.gpio = Button(
                pin=self._pin_num,
                pull_up=_pull_up,
                bounce_time=float(bouncetime / 1000),
            )
            self._bouncetime = bouncetime
        else:
            if bouncetime != self._bouncetime:
                pressed_handler = self.gpio.when_activated
                released_handler = self.gpio.when_deactivated
                self.gpio.close()
                self.gpio = Button(
                    pin=self._pin_num,
                    pull_up=_pull_up,
                    bounce_time=float(bouncetime / 1000),
                )
                self._bouncetime = bouncetime

        if trigger in [None, self.IRQ_FALLING]:
            pressed_handler = handler
        elif trigger in [self.IRQ_RISING]:
            released_handler = handler
        elif trigger in [self.IRQ_RISING_FALLING]:
            pressed_handler = handler
            released_handler = handler

        if pressed_handler is not None:
            self.gpio.when_pressed = pressed_handler
        if released_handler is not None:
            self.gpio.when_released = released_handler

    def name(self):
        """
        Get the GPIO pin name.

        Returns:
            str: The GPIO pin name.
        """
        return f"GPIO{self._pin_num}"
