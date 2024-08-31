# #!/usr/bin/env python3
# """
# Robot Hat Library
# """
# from .adc import ADC
# from .filedb import fileDB
# from .i2c import I2C
# from .music import Music
# from .motor import Motor, Motors
# from .pin import Pin
# from .pwm import PWM
# from .servo import Servo
# from .grayscale import Grayscale_Module
# from .utils import reset_mcu, run_command, mapping, is_installed, get_battery_voltage
# from .robot import Robot
# from .ultrasonic import Ultrasonic


# def __usage__():
#     print("Usage: robot_hat [reset_mcu]")
#     quit()


# def __main__():
#     import sys

#     if len(sys.argv) == 2:
#         if sys.argv[1] == "reset_mcu":
#             reset_mcu()
#             print("Onboard MCU reset.")
#     else:
#         __usage__()


# __all__ = [
#     "Ultrasonic",
#     "Robot",
#     "Grayscale_Module",
#     "Servo",
#     "ADC",
#     "I2C",
#     "Music",
#     "Motor",
#     "Motors",
#     "Pin",
#     "PWM",
#     "fileDB",
#     "run_command",
#     "mapping",
#     "is_installed",
#     "get_battery_voltage",
# ]
