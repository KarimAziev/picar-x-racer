from app.util.os_checks import is_raspberry_pi
from app.modules.vilib import Vilib
from app.robot_hat.filedb import fileDB

is_os_raspberry = is_raspberry_pi()

if is_os_raspberry:
    from app.robot_hat.grayscale import ADC
    from app.robot_hat.servo import Servo
    from app.robot_hat.pwm import PWM
    from app.robot_hat.adc import ADC
    from app.robot_hat.pin import Pin
    from app.robot_hat.ultrasonic import Ultrasonic
    from app.robot_hat.grayscale import Grayscale_Module
    from app.robot_hat.utils import (
        reset_mcu,
        get_ip,
        run_command,
        is_installed,
        mapping,
        get_battery_voltage,
    )
    from app.modules.picarx import Picarx
else:
    from app.robot_hat.mock.ultrasonic import Ultrasonic
    from app.robot_hat.mock.grayscale_mock import Grayscale_Module
    from app.robot_hat.mock.servo_mock import Servo
    from app.robot_hat.mock.pwm_mock import PWM
    from app.robot_hat.mock.pin_mock import Pin
    from app.robot_hat.mock.adc_mock import ADC
    from app.mock.picarx import Picarx
    from app.mock.robot_hat_fake_utils import (
        reset_mcu,
        get_ip,
        run_command,
        is_installed,
        mapping,
        get_battery_voltage,
    )

Picarx = Picarx

reset_mcu = reset_mcu
get_ip = get_ip
run_command = run_command
is_installed = is_installed
mapping = mapping
get_battery_voltage = get_battery_voltage
Pin = Pin
ADC = ADC
PWM = PWM
Servo = Servo
fileDB = fileDB
Grayscale_Module = Grayscale_Module
Ultrasonic = Ultrasonic

__all__ = [
    "Vilib",
    "reset_mcu",
    "get_ip",
    "run_command",
    "is_installed",
    "mapping",
    "get_battery_voltage",
    "Ultrasonic",
    "Grayscale_Module",
    "Servo",
    "PWM",
    "Pin",
    "ADC",
    "fileDB",
    "Picarx",
]
