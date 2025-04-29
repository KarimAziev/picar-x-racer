"""
Sound Location Recognition Module Communication Protocol

1. Communication format:
   - The master randomly sends 16-bit data to the slave, and then receives 16-bit data.
   - The 16-bit format received by the master:
       (1) First receive the lower 8 bits of the data, and then receive the upper 8 bits.
       (2) Comply with MSB (Most Significant Bit) transmission.

2. Direction Detection:
   - The module can detect a full 360-degree direction, with the minimum detection unit of 20 degrees.
   - The valid data range is from 0 to 355 degrees.

3. Communication Process:
   - The master pulls up the BUSY line. The 064B (TR16F064B) starts monitoring the direction.
   - Once the 064B recognizes the direction, it pulls down the BUSY line (which is normally high).
   - The master, upon detecting the BUSY line pulled low, sends 16 bits of arbitrary data to the 064B,
     and then receives 16 bits of data in response.
   - After the reception is completed, the master pulls up the BUSY line and resumes direction detection.
"""

from typing import List, Union

import spidev
from gpiozero import InputDevice


class SoundDirection:
    """
    A class to communicate with the sound location recognition module using SPI.
    """

    CS_DELAY_US: int = 500  # Chip select delay in microseconds.
    CLOCK_SPEED: int = 10_000_000  # SPI clock speed: 10 MHz.

    def __init__(
        self, busy_pin: Union[int, str] = 6, spi_bus: int = 0, spi_dev: int = 0
    ) -> None:
        """
        Initializes the SoundDirection instance by setting up SPI communication
        and configuring the BUSY pin.

        Args:
            busy_pin: The GPIO pin used to detect the BUSY signal.
            spi_bus: The SPI bus number that the sound module is connected to (e.g., 0).
            spi_dev: The SPI device (chip select) number that the sound module is connected to (e.g., 0)
        """
        self.spi: spidev.SpiDev = spidev.SpiDev()

        self.spi.open(spi_bus, spi_dev)

        # Configure the GPIO input for the BUSY line.
        self.busy: InputDevice = InputDevice(busy_pin, pull_up=False)

    def read(self) -> int:
        """
        Reads the sound direction data via SPI.

        This method sends a dummy SPI command and receives a list of 6 bytes.
        The direction data is contained within the 5th and 6th elements (index 4 and 5) of
        the received list. If the upper byte equals 255, it returns -1 to indicate an error.
        Otherwise, it computes the angle by combining the two bytes and adjusting
        the value according to the sensor's conversion (val = (360 + 160 - val) % 360).

        Returns:
            int: The detected sound direction in degrees (0 to 359), or -1 if an error occurs.
        """
        result: List[int] = self.spi.xfer2(
            [0, 0, 0, 0, 0, 0], self.CLOCK_SPEED, self.CS_DELAY_US
        )

        # Extract the lower and higher 8-bit values from the received data.
        l_val, h_val = result[4:]

        if h_val == 255:
            return -1
        else:
            # Combine bytes into a single 16-bit integer.
            val: int = (h_val << 8) + l_val
            val = (360 + 160 - val) % 360
            return val

    def isdetected(self) -> bool:
        """
        Checks if a sound direction has been detected.

        The method reads the state of the BUSY line. When the sensor detects a sound,
        it pulls the BUSY line low (i.e., value becomes 0).

        Returns:
            bool: True if the BUSY pin is detected as low (sound detected), False otherwise.
        """
        return self.busy.value == 0


if __name__ == "__main__":
    from time import sleep

    sd: SoundDirection = SoundDirection()
    while True:
        if sd.isdetected():
            print(f"Sound detected at {sd.read()} degrees")
        sleep(0.2)
