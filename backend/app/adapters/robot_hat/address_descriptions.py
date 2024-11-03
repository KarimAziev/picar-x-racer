ADDRESS_DESCRIPTIONS = {
    0x44: "(PWM period, timer 0)",
    0x45: "(PWM period, timer 1)",
    0x46: "(PWM period, timer 2)",
    0x47: "(PWM period, timer 3)",
    0x20: "(PWM channel 0 On Value)",
    0x21: "(PWM channel 1 On Value)",
    0x22: "(PWM channel 2 On Value)",
    0x23: "(PWM channel 3 On Value)",
    0x24: "(PWM channel 4 On Value)",
    0x25: "(PWM channel 5 On Value)",
    0x26: "(PWM channel 6 On Value)",
    0x27: "(PWM channel 7 On Value)",
    0x28: "(PWM channel 8 On Value)",
    0x29: "(PWM channel 9 On Value)",
    0x2A: "(PWM channel 10 On Value)",
    0x2B: "(PWM channel 11 On Value)",
    0x2C: "(Motor 2 speed On Value)",
    0x2D: "(Motor 1 speed On Value)",
    0x40: "(Timer 0 Prescaler)",
    0x41: "(Timer 1 Prescaler)",
    0x42: "(Timer 2 Prescaler)",
    0x43: "(Timer 3 Prescaler)",
    0x170000: "(ADC channel 0)",
    0x160000: "(ADC channel 1)",
    0x150000: "(ADC channel 2)",
    0x140000: "(ADC channel 3)",
    0x130000: "(ADC channel 4: Battery Level)",
}

VALUE_DESCRIPTIONS = {
    0xB004: "0xB004",
}


def get_address_description(address):
    return ADDRESS_DESCRIPTIONS.get(address, "")


def get_value_description(value):
    return VALUE_DESCRIPTIONS.get(value, "")
