from app.config.platform import is_os_raspberry


def get_battery_voltage() -> float:
    """
    Retrieves the battery voltage from an ADC (Analog-to-Digital Converter) hardware on a Raspberry Pi
    or a mocked value on other systems.

    - On a Raspberry Pi, the function uses the actual hardware ADC interface.
    - On other platforms (e.g., local development or testing), it uses a mock ADC implementation.

    The function reads the raw voltage from the ADC on the A4 channel,
    applies a scaling factor, and rounds the result to two decimal places.

    Returns:
        float: The scaled battery voltage in volts (e.g., 7.3).
    """
    if is_os_raspberry:
        from app.adapters.robot_hat.adc import ADC
    else:
        from app.adapters.robot_hat.mock.adc_mock import ADC

    adc = ADC("A4")
    raw_voltage = adc.read_voltage()
    voltage = round(raw_voltage * 3, 2)
    return voltage
