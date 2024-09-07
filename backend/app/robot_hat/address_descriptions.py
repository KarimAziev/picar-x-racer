ADDRESS_DESCRIPTIONS = {
    0x44: "(Set PWM period, timer 0)",
    0x45: "(Set PWM period, timer 1)",
    0x46: "(Set PWM period, timer 2)",
    0x47: "(Set PWM period, timer 3)",
    0x20: "(Set PWM channel 0 On Value)",
    0x21: "(Set PWM channel 1 On Value)",
    0x22: "(Set PWM channel 2 On Value)",
    0x23: "(Set PWM channel 3 On Value)",
    0x24: "(Set PWM channel 4 On Value)",
    0x25: "(Set PWM channel 5 On Value)",
    0x26: "(Set PWM channel 6 On Value)",
    0x27: "(Set PWM channel 7 On Value)",
    0x28: "(Set PWM channel 8 On Value)",
    0x29: "(Set PWM channel 9 On Value)",
    0x2A: "(Set PWM channel 10 On Value)",
    0x2B: "(Set PWM channel 11 On Value)",
    0x2C: "(Set Motor 2 speed On Value)",
    0x2D: "(Set Motor 1 speed On Value)",
    0x40: "(Set timer 0 Prescaler)",
    0x41: "(Set timer 1 Prescaler)",
    0x42: "(Set timer 2 Prescaler)",
    0x43: "(Set timer 3 Prescaler)",
    0x170000: "(ADC channel 0)",
    0x160000: "(ADC channel 1)",
    0x150000: "(ADC channel 2)",
    0x140000: "(ADC channel 3)",
    0x130000: "(ADC channel 4: Battery Level)"
}

VALUE_DESCRIPTIONS = {
    0xB004: "0xB004",
}

def get_address_description(address):
    return ADDRESS_DESCRIPTIONS.get(address, "")

def get_value_description(value):
    return VALUE_DESCRIPTIONS.get(value, "")
