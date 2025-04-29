"""
Driver for controlling an I2C RGB LED strip with multiple animation styles.
"""

import math
import time
from typing import Dict, List, Literal, Sequence, Union

import numpy as np
from smbus2 import SMBus

RGBStyle = Literal[
    "monochromatic",
    "breath",
    "boom",
    "bark",
    "speak",
    "listen",
]


class RGBStrip:
    """
    Driver for an RGB LED strip based on the SLED1735 chip.
    This class provides several display modes and animations.
    """

    # Preset colors, mapping a name to an RGB triple.
    PRESET_COLORS: Dict[str, List[int]] = {
        "white": [255, 255, 255],
        "black": [0, 0, 0],
        "red": [255, 0, 0],
        "yellow": [255, 225, 0],
        "green": [0, 255, 0],
        "blue": [0, 0, 255],
        "cyan": [0, 255, 255],
        "magenta": [255, 0, 255],
        "pink": [255, 100, 100],
    }

    # Supported display styles.
    DISPLAY_STYLES: List[RGBStyle] = [
        "monochromatic",
        "breath",
        "boom",
        "bark",
        "speak",
        "listen",
    ]

    MIN_FRAME_DELAY: float = 0.05

    # --- Register and constant definitions ---
    CONFIGURE_CMD_PAGE: int = 0xFD
    FRAME1_PAGE: int = 0x00
    FRAME2_PAGE: int = 0x01
    FUNCTION_PAGE: int = 0x0B
    LED_VAF_PAGE: int = 0x0D

    CONFIGURATION_REG: int = 0x00
    PICTURE_DISPLAY_REG: int = 0x01
    DISPLAY_OPTION_REG: int = 0x05
    BREATH_CTL_REG: int = 0x08
    BREATH_CTL_REG2: int = 0x09
    SW_SHUT_DOWN_REG: int = 0x0A

    AUDIO_GAIN_CTL_REG: int = 0x0B
    STAGGERED_DELAY_REG: int = 0x0D
    SLEW_RATE_CTL_REG: int = 0x0E
    CURRENT_CTL_REG: int = 0x0F
    VAF_CTL_REG: int = 0x14
    VAF_CTL_REG2: int = 0x15

    MASK_STD_GROUP1: int = 0x3 << 0
    MASK_STD_GROUP2: int = 0x3 << 2
    MASK_STD_GROUP3: int = 0x3 << 4
    MASK_STD_GROUP4: int = 0x3 << 6
    CONST_STD_GROUP1: int = 0x00
    CONST_STD_GROUP2: int = 0x55
    CONST_STD_GROUP3: int = 0xAA
    CONST_STD_GROUP4: int = 0xFF

    MASK_VAF1: int = 0x4 << 0
    MASK_VAF2: int = 0x4 << 4
    MASK_VAF3: int = 0x4 << 0
    MASK_FORCE_VAF_TIME_CONST: int = 0x0 << 3
    MASK_FORCE_VAF_CTL_ALWAYS_ON: int = 0x0 << 6
    MASK_FORCE_VAF_CTL_DISABLE: int = 0x2 << 6
    MASK_CURRENT_CTL_ENABLE: int = 0x1 << 7
    CONST_CURRENT_STEP_20mA: int = 0x19 << 0
    MASK_BLINK_FRAME_300: int = 0x0 << 6
    MASK_BLINK_ENABLE: int = 0x1 << 3
    MASK_BLINK_DISABLE: int = 0x0 << 3
    MASK_BLINK_PERIOD_TIME_CONST: int = 0x7 << 0

    TYPE3_VAF: List[int] = [
        # Frame 1 (bytes for each LED channel group)
        0x50,
        0x55,
        0x55,
        0x55,  # C1-A ~ C1-P
        0x00,
        0x00,
        0x00,
        0x00,  # C2-A ~ C2-P
        0x00,
        0x00,
        0x00,
        0x00,  # C3-A ~ C3-P
        0x15,
        0x54,
        0x55,
        0x55,  # C4-A ~ C4-P
        0x00,
        0x00,
        0x00,
        0x00,  # C5-A ~ C5-P
        0x00,
        0x00,
        0x00,
        0x00,  # C6-A ~ C6-P
        0x55,
        0x05,
        0x55,
        0x55,  # C7-A ~ C7-P
        0x00,
        0x00,
        0x00,
        0x00,  # C8-A ~ C8-P
        # Frame 2
        0x00,
        0x00,
        0x00,
        0x00,  # C9-A ~ C9-P
        0x55,
        0x55,
        0x41,
        0x55,  # C10-A ~ C10-P
        0x00,
        0x00,
        0x00,
        0x00,  # C11-A ~ C11-P
        0x00,
        0x00,
        0x00,
        0x00,  # C12-A ~ C12-P
        0x55,
        0x55,
        0x55,
        0x50,  # C13-A ~ C13-P
        0x00,
        0x00,
        0x00,
        0x00,  # C14-A ~ C14-P
        0x00,
        0x00,
        0x00,
        0x00,  # C15-A ~ C15-P
        0x00,
        0x00,
        0x00,
        0x00,  # C16-A ~ C16-P
    ]

    def __init__(self, address: int = 0x74, num_lights: int = 8) -> None:
        """
        Initialize the RGB strip driver and perform a hardware initialization.

        Parameters:
            address: The I2C address of the LED controller.
            num_lights: The number of lights (LEDs) on the strip.
        """
        self.num_lights: int = num_lights
        self.current_style: Union[RGBStyle, None] = "breath"
        self.current_color: List[int] = self.PRESET_COLORS[
            "white"
        ]  # default to white (RGB list)
        self.brightness: float = 1.0
        self.frame_delay: float = 0.1
        self.frame_buffer: List[List[List[int]]] = []
        self.current_frame_index: int = 0
        self.beats_per_second: float = 1.5
        self.change_mode_flag: bool = False
        self.max_frames: int = 1  # This will be recalculated during mode change

        # Initialize I2C bus and device address.
        self.bus: SMBus = SMBus(1)
        self.address: int = address

        # Set up the device registers.
        self.write_command(self.CONFIGURE_CMD_PAGE, self.FUNCTION_PAGE)
        # Put system into software shutdown mode during initialization.
        self.write_command(self.SW_SHUT_DOWN_REG, 0x0)
        # Set matrix type.
        self.write_command(self.PICTURE_DISPLAY_REG, 0x10)

        # Configure staggered delay.
        stagger_value: int = (
            (self.MASK_STD_GROUP4 & self.CONST_STD_GROUP4)
            | (self.MASK_STD_GROUP3 & self.CONST_STD_GROUP3)
            | (self.MASK_STD_GROUP2 & self.CONST_STD_GROUP2)
            | (self.MASK_STD_GROUP1 & self.CONST_STD_GROUP1)
        )
        self.write_command(self.STAGGERED_DELAY_REG, stagger_value)

        self.write_command(self.SLEW_RATE_CTL_REG, 0x1)  # Enable slew rate control
        # Set VAF control based on LED type.
        self.write_command(self.VAF_CTL_REG, (self.MASK_VAF2 | self.MASK_VAF1))
        self.write_command(
            self.VAF_CTL_REG2,
            (
                self.MASK_FORCE_VAF_CTL_DISABLE
                | self.MASK_FORCE_VAF_TIME_CONST
                | self.MASK_VAF3
            ),
        )
        # Set LED driving current to 20mA and enable current control.
        self.write_command(
            self.CURRENT_CTL_REG,
            (self.MASK_CURRENT_CTL_ENABLE | self.CONST_CURRENT_STEP_20mA),
        )

        # Initialize Frame 1 page (clear RAM).
        self.write_command(self.CONFIGURE_CMD_PAGE, self.FRAME1_PAGE)
        self.write_multiple_data(0x00, 0x00, 0xB3)
        # Clear Frame 2 page.
        self.write_command(self.CONFIGURE_CMD_PAGE, self.FRAME2_PAGE)
        self.write_multiple_data(0x00, 0x00, 0xB3)

        self.write_command(self.CONFIGURE_CMD_PAGE, self.LED_VAF_PAGE)
        self.write_multiple_data(0x00, self.TYPE3_VAF, 0x40)
        self.write_command(self.CONFIGURE_CMD_PAGE, self.FUNCTION_PAGE)
        # Return system to normal (software) mode.
        self.write_command(self.SW_SHUT_DOWN_REG, 0x1)
        self.write_command(self.CONFIGURE_CMD_PAGE, self.FRAME1_PAGE)
        # Clear LED control registers on Frame 1 page.
        self.write_multiple_data(0x00, 0xFF, 0x10)
        self.write_multiple_data(0x20, 0x00, 0x80)
        self.write_command(self.CONFIGURE_CMD_PAGE, self.FRAME2_PAGE)
        # Clear LED control registers on Frame 2 page.
        self.write_multiple_data(0x00, 0xFF, 0x10)
        self.write_multiple_data(0x20, 0x00, 0x80)

    def write_command(self, register: int, command: int) -> None:
        """
        Write a single command byte to a register via I2C.

        Parameters:
            register: The register address.
            command: The command byte to write.
        """
        self.bus.write_byte_data(self.address, register, command)

    def write_multiple_data(
        self, start_register: int, data: Union[int, List[int]], num_bytes: int
    ) -> None:
        """
        Write data repeatedly or from a list to consecutive registers.

        Parameters:
            start_register: The starting register address.
            data: Either an integer value for repeated writes or a list of values.
            num_bytes: The number of bytes to write.
        """
        register_addr: int = start_register
        if isinstance(data, int):
            for _ in range(num_bytes):
                self.write_command(register_addr, data)
                register_addr += 1
        elif isinstance(data, list):
            for i in range(num_bytes):
                self.write_command(register_addr, data[i])
                register_addr += 1

    def display(self, rgb_frame: List[List[int]]) -> None:
        """
        Display the current RGB frame to the LED strip.
        The data is arranged per color channel and sent to specific registers.

        Parameters:
            rgb_frame: A list of [red, green, blue] values for each LED.
        """
        # Split the frame into red, green, and blue lists.
        red_values: List[int] = [pixel[0] for pixel in rgb_frame]
        green_values: List[int] = [pixel[1] for pixel in rgb_frame]
        blue_values: List[int] = [pixel[2] for pixel in rgb_frame]
        color_channels: List[List[int]] = [red_values, green_values, blue_values]

        # The starting register for data on the LED strip.
        register_address: int = 0x20
        insertion_index: int = 0  # position to insert filler zeros
        data_segment_index: int = 0  # index for segmenting the channel data

        for channel_index in range(3):
            # Set the appropriate frame page.
            if channel_index == 0:
                self.write_command(self.CONFIGURE_CMD_PAGE, self.FRAME1_PAGE)
            elif register_address == 0x20:
                self.write_command(self.CONFIGURE_CMD_PAGE, self.FRAME2_PAGE)

            # Select the current color channel.
            current_channel: int = channel_index % 3
            # Extract a segment of 14 values from the current channel.
            segment: List[int] = color_channels[current_channel][
                data_segment_index * 14 : (data_segment_index + 1) * 14
            ]
            # Insert two filler zeros at the specified positions.
            segment.insert(insertion_index, 0)
            segment.insert(insertion_index + 1, 0)

            self.bus.write_i2c_block_data(self.address, register_address, segment)
            if current_channel == 2:
                insertion_index += 3
                data_segment_index += 1
            register_address += 0x10
            if register_address == 0xA0:
                register_address = 0x20

    def calculate_monochromatic(self) -> List[int]:
        """
        Calculate a monochromatic frame by scaling the base color with brightness.

        Returns:
            A list representing the RGB values after brightness scaling.
        """
        return [int(component * self.brightness) for component in self.current_color]

    def calculate_normal_distribution(
        self,
        expected_value: float,
        sigma: float,
        amplitude: float,
        position: int,
        offset: float,
    ) -> float:
        """
        Calculate the normal (Gaussian) distribution value for a given position.

        Parameters:
            expected_value: The mean (center) value of the distribution.
            sigma: The standard deviation controlling the spread.
            amplitude: Scaling factor for the peak.
            position: The x position where the distribution is evaluated.
            offset: A shift added to the computed value.

        Returns:
            The calculated value of the normal distribution at the given position.
        """
        gaussian: float = (
            amplitude
            * np.exp(-((position - expected_value) ** 2) / (2 * sigma**2))
            / (math.sqrt(2 * math.pi) * sigma)
        ) + offset
        return gaussian

    def calculate_cos_value(
        self,
        peak_value: float,
        multiplier: float,
        x_value: float,
        phase_offset: float = 0.0,
    ) -> float:
        """
        Calculate a cosine-based value for animation.

        Parameters:
            peak_value: The maximum peak value.
            multiplier: A scaling multiplier that affects the period.
            x_value: The x value (often the frame index).
            phase_offset: A phase offset in radians.

        Returns:
            The computed cosine value adjusted to a range [0, peak_value].
        """
        return (peak_value / 2.0) * math.cos(multiplier * x_value + phase_offset) + (
            peak_value / 2.0
        )

    def calculate_breath_frame(
        self, frame_idx: int, led_idx: int, amplitude: float = 5, sigma: float = 2
    ) -> List[int]:
        """
        Calculate the LED brightness for the "breath" style animation.
        In this style, brightness rises from dark to bright and then dims down.

        Parameters:
            frame_idx: The current frame index.
            led_idx: The index of the LED.
            amplitude: Amplitude scaling for the distribution.
            sigma: Standard deviation for the Gaussian curve.

        Returns:
            A list with adjusted RGB values for the selected LED.
        """
        center: int = 5
        base_color: List[float] = [c * self.brightness for c in self.current_color]
        angle_multiplier: float = (2 * math.pi) / self.max_frames
        phase_offset: float = -self.calculate_cos_value(1, angle_multiplier, frame_idx)
        brightness_scale: float = self.calculate_normal_distribution(
            center, sigma, amplitude, led_idx, phase_offset
        )
        return [max(0, int(component * brightness_scale)) for component in base_color]

    def calculate_boom_frame(
        self, frame_idx: int, led_idx: int, amplitude: float = 5, sigma: float = 2
    ) -> List[int]:
        """
        Calculate the LED brightness for the "boom" style animation.
        In this style, brightness increases from the middle outward on each side.

        Parameters:
            frame_idx: The current frame index.
            led_idx: The index of the LED.
            amplitude: Amplitude scaling for the distribution.
            sigma: Standard deviation for the Gaussian curve.

        Returns:
            A list with adjusted RGB values for the selected LED.
        """
        center: int = 5
        base_color: List[float] = [c * self.brightness for c in self.current_color]
        angle_multiplier: float = (2 * math.pi) / (self.max_frames * 2.0)
        phase_offset: float = -self.calculate_cos_value(1, angle_multiplier, frame_idx)
        brightness_scale: float = self.calculate_normal_distribution(
            center, sigma, amplitude, led_idx, phase_offset
        )
        return [max(0, int(component * brightness_scale)) for component in base_color]

    def calculate_bark_frame(
        self, frame_idx: int, led_idx: int, amplitude: float = 2.5, sigma: float = 1
    ) -> List[int]:
        """
        Calculate the LED brightness for the "bark" style animation.
        This style creates a brightness pattern that peaks at the center and falls off toward the edges.

        Parameters:
            frame_idx: The current frame index.
            led_idx: The index of the LED.
            amplitude: Amplitude scaling for the distribution.
            sigma: Standard deviation for the Gaussian curve.

        Returns:
            A list with adjusted RGB values for the selected LED.
        """
        base_color: List[float] = [c * self.brightness for c in self.current_color]
        half_length: float = (self.num_lights - 1) / 2.0
        angle_multiplier: float = (2 * math.pi) / (self.max_frames * 2.0)
        offset_center: float = self.calculate_cos_value(
            half_length, angle_multiplier, frame_idx
        )
        expected_center: float = (
            offset_center if led_idx <= half_length else 2 * half_length - offset_center
        )
        brightness_scale: float = self.calculate_normal_distribution(
            expected_center, sigma, amplitude, led_idx, 0
        )
        return [max(0, int(component * brightness_scale)) for component in base_color]

    def calculate_speak_frame(
        self, frame_idx: int, led_idx: int, amplitude: float = 2.5, sigma: float = 1
    ) -> List[int]:
        """
        Calculate the LED brightness for the "speak" style animation.
        In this mode, brightness moves from the center outward and then back to the center.

        Parameters:
            frame_idx: The current frame index.
            led_idx: The index of the LED.
            amplitude: Amplitude scaling for the distribution.
            sigma: Standard deviation for the Gaussian curve.

        Returns:
            A list with adjusted RGB values for the selected LED.
        """
        base_color: List[float] = [c * self.brightness for c in self.current_color]
        half_length: float = (self.num_lights - 1) / 2.0
        angle_multiplier: float = (2 * math.pi) / self.max_frames
        offset_center: float = self.calculate_cos_value(
            half_length, angle_multiplier, frame_idx
        )
        expected_center: float = (
            offset_center if led_idx <= half_length else 2 * half_length - offset_center
        )
        brightness_scale: float = self.calculate_normal_distribution(
            expected_center, sigma, amplitude, led_idx, 0
        )
        return [max(0, int(component * brightness_scale)) for component in base_color]

    def calculate_listen_frame(
        self, frame_idx: int, led_idx: int, amplitude: float = 2.5, sigma: float = 1
    ) -> List[int]:
        """
        Calculate the LED brightness for the "listen" style animation.
        The brightness pattern moves from the middle toward the left, then across to the right,
        and finally back toward the center.

        Parameters:
            frame_idx: The current frame index.
            led_idx: The index of the LED.
            amplitude: Amplitude scaling for the distribution.
            sigma: Standard deviation for the Gaussian curve.

        Returns:
            A list with adjusted RGB values for the selected LED.
        """
        base_color: List[float] = [c * self.brightness for c in self.current_color]
        max_index: int = self.num_lights - 1
        angle_multiplier: float = (2 * math.pi) / self.max_frames
        phase_offset: float = math.pi / 2  # Phase offset to shift pattern to the left.
        expected_center: float = self.calculate_cos_value(
            float(max_index), angle_multiplier, frame_idx, phase_offset
        )
        brightness_scale: float = self.calculate_normal_distribution(
            expected_center, sigma, amplitude, led_idx, 0
        )
        return [max(0, int(component * brightness_scale)) for component in base_color]

    def convert_color(self, input_color: Union[str, int, Sequence[int]]) -> List[int]:
        """
        Convert an input color in various formats to an RGB list.
        Acceptable input formats include:
          - A predefined color name (e.g. "white")
          - An HTML hex string (e.g. "#a2c20c")
          - An integer representation (e.g. 0xa2c20c)
          - A list or tuple of three values (e.g. [170, 192, 12])

        Parameters:
            input_color: The color provided in one of the accepted formats.

        Returns:
            An RGB list with values in the range 0-255.
        """
        if isinstance(input_color, str):
            lower_color = input_color.lower()
            if lower_color in self.PRESET_COLORS:
                return self.PRESET_COLORS[lower_color]
            elif input_color.startswith("#") and len(input_color) == 7:
                return [
                    int(input_color[1:3], 16),
                    int(input_color[3:5], 16),
                    int(input_color[5:7], 16),
                ]
            else:
                raise ValueError("Invalid color string: {}".format(input_color))
        elif isinstance(input_color, (list, tuple)) and len(input_color) == 3:
            return [int(component) for component in input_color]
        elif isinstance(input_color, int):
            return [
                (input_color >> 16) & 0xFF,
                (input_color >> 8) & 0xFF,
                input_color & 0xFF,
            ]
        else:
            raise ValueError("Unsupported color format: {}".format(input_color))

    def set_mode(
        self,
        style: RGBStyle = "breath",
        color: Union[str, int, Sequence[int]] = "white",
        beats_per_second: float = 1.0,
        brightness: float = 1.0,
    ) -> None:
        """
        Set the display mode, color, animation speed, and brightness for the LED strip.
        The mode will be changed on the next frame update.

        Parameters:
            style: The display style, e.g. "breath" or "boom".
            color: The desired color in any accepted format.
            beats_per_second: How many cycles should repeat per second.
            brightness: The brightness factor in the range 0.0 to 1.0.
        """
        if style not in self.DISPLAY_STYLES:
            raise ValueError("Invalid style: {}".format(style))
        self.current_style = style
        self.current_color = self.convert_color(color)
        self.beats_per_second = float(beats_per_second)
        self.brightness = float(brightness)
        self.change_mode_flag = True

    def calculate_frame_data(self, frame_idx: int, led_idx: int) -> List[int]:
        """
        Calculate the RGB value for a single LED based on the current style
        and animation parameters.

        Parameters:
            frame_idx: The current frame index.
            led_idx: The index of the LED.

        Returns:
            A list with the computed RGB values.
        """
        if self.current_style == "monochromatic":
            return self.calculate_monochromatic()
        elif self.current_style == "breath":
            return self.calculate_breath_frame(frame_idx, led_idx)
        elif self.current_style == "boom":
            return self.calculate_boom_frame(frame_idx, led_idx)
        elif self.current_style == "bark":
            return self.calculate_bark_frame(frame_idx, led_idx)
        elif self.current_style == "speak":
            return self.calculate_speak_frame(frame_idx, led_idx)
        elif self.current_style == "listen":
            return self.calculate_listen_frame(frame_idx, led_idx)
        else:
            return [0, 0, 0]

    def show(self) -> None:
        """
        Update the LED strip to show the current animation frame.
        If the display mode has changed, the animation frames are recalculated.
        """
        if self.current_style is not None:
            if self.change_mode_flag:
                self.change_mode_flag = False
                self.frame_buffer.clear()
                self.max_frames = int(1 / self.beats_per_second / self.MIN_FRAME_DELAY)
                for frame_idx in range(self.max_frames):
                    frame: List[List[int]] = []
                    for led_idx in range(self.num_lights):
                        pixel_data: List[int] = self.calculate_frame_data(
                            frame_idx, led_idx
                        )
                        frame.append(pixel_data)
                    # Uncomment for debugging frame data:
                    # print("{}:{}".format(frame_idx, frame))
                    self.frame_buffer.append(frame)
            # Cycle through the precomputed frames.
            if self.current_frame_index >= self.max_frames:
                self.current_frame_index = 0
            self.display(self.frame_buffer[self.current_frame_index])
            self.current_frame_index += 1
            time.sleep(self.MIN_FRAME_DELAY)
        else:
            time.sleep(self.MIN_FRAME_DELAY)

    def close(self) -> None:
        """
        Shutdown the LED strip by turning off all lights.
        """
        self.current_style = None
        self.change_mode_flag = True
        off_frame: List[List[int]] = [[0, 0, 0] for _ in range(self.num_lights)]
        self.display(off_frame)
        time.sleep(self.MIN_FRAME_DELAY)


if __name__ == "__main__":
    rgb_strip = RGBStrip(address=0x74, num_lights=11)
    # Uncomment one of the following to choose the display mode:
    # rgb_strip.set_mode(style="monochromatic", color="white", beats_per_second=5, brightness=1)
    # rgb_strip.set_mode(style="breath", color="pink", beats_per_second=1.5, brightness=1)
    # rgb_strip.set_mode(style="boom", color="yellow", beats_per_second=2.5, brightness=1)
    # rgb_strip.set_mode(style="bark", color="red", beats_per_second=2.5, brightness=1)
    # rgb_strip.set_mode(style="speak", color="magenta", beats_per_second=1, brightness=1)
    rgb_strip.set_mode(style="listen", color="cyan", beats_per_second=0.5, brightness=1)
    try:
        while True:
            rgb_strip.show()
    except KeyboardInterrupt:
        pass
    finally:
        rgb_strip.close()
        print("Closing LED strip while exiting.")
