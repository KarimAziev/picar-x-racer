from app.config.platform import is_raspberry_pi


def get_battery_voltage():
    """
    Get battery voltage

    :return: battery voltage(V)
    :rtype: float
    """
    if is_raspberry_pi:
        from app.adapters.robot_hat.adc import ADC
    else:
        from app.adapters.robot_hat.mock.adc_mock import ADC
    adc = ADC("A4")
    raw_voltage = adc.read_voltage()
    voltage = raw_voltage * 3
    return voltage
