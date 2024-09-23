from app.robot_hat.mock.pin_mock import Pin

"""
This module provides mock implementations of the "robot_hat.utils" functions to
facilitate development on non-Raspberry Pi operating systems.

These mock functions simulate the behavior of the original functions without
requiring actual hardware, allowing for testing and development in environments
where the Raspberry Pi hardware is not available.
"""

import asyncio
import os
import re

from .battery import Battery


def run_command(cmd):
    """
    Run command and return status and output

    :param cmd: command to run
    :type cmd: str
    :return: status, output
    :rtype: tuple
    """
    import subprocess

    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    result = p.stdout.read().decode("utf-8") if p.stdout is not None else ""
    status = p.poll()
    return status, result


def is_installed(cmd):
    """
    Check if command is installed

    :param cmd: command to check
    :type cmd: str
    :return: True if installed
    :rtype: bool
    """
    status, _ = run_command(f"which {cmd}")
    if status in [
        0,
    ]:
        return True
    else:
        return False


def mapping(x, in_min, in_max, out_min, out_max):
    """
    Map value from one range to another range

    :param x: value to map
    :type x: float/int
    :param in_min: input minimum
    :type in_min: float/int
    :param in_max: input maximum
    :type in_max: float/int
    :param out_min: output minimum
    :type out_min: float/int
    :param out_max: output maximum
    :return: mapped value
    :rtype: float/int
    """
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def get_ip(ifaces=["wlan0", "eth0"]):
    """
    Get IP address

    :param ifaces: interfaces to check
    :type ifaces: list
    :return: IP address or False if not found
    :rtype: str/False
    """
    if isinstance(ifaces, str):
        ifaces = [ifaces]
    for iface in list(ifaces):
        search_str = "ip addr show {}".format(iface)
        result = os.popen(search_str).read()
        com = re.compile(r"(?<=inet )(.*)(?=\/)", re.M)
        ipv4 = re.search(com, result)
        if ipv4:
            ipv4 = ipv4.groups()[0]
            return ipv4
    return False


async def reset_mcu():
    """
    Reset mcu on Robot Hat.

    This is helpful if the mcu somehow stuck in a I2C data
    transfer loop, and Raspberry Pi getting IOError while
    Reading ADC, manipulating PWM, etc.
    """
    mcu_reset = Pin("MCURST")
    mcu_reset.off()
    await asyncio.sleep(0.01)
    mcu_reset.on()
    await asyncio.sleep(0.01)

    mcu_reset.close()


battery = Battery()


def get_battery_voltage():
    """
    Generate the total battery voltage by simulating the reading from two 18650 batteries.

    This function simulates the behavior of reading battery voltage from two 18650 lithium-ion batteries,
    which typically have a nominal voltage of around 3.7V but can range between 3.0V (fully discharged)
    and 4.2V (fully charged). It returns a randomly generated value within this range for each battery
    and sums them to provide the total voltage.

    Example:
        If the first battery voltage is 3.8V and the second battery voltage is 4.1V,
        the total voltage returned by this function would be 3.8 + 4.1 = 7.9V.

    :return: The total battery voltage in volts (V), which is a sum of two battery voltages.
    :rtype: float
    """
    return battery.get_battery_voltage()
