from __future__ import annotations

from math import pi
from typing import Final

# gravitational acceleration in m/s²
G: Final[float] = 9.81
SEC_IN_H: Final[float] = 3600.0  # number of seconds in an hour
MM_IN_M: Final[float] = 1000.0  # millimeters in a meter


def max_speed_loaded_kmh(
    mass_kg: float,
    wheel_diameter_mm: float,
    stall_torque_kgcm: float,
    rpm_no_load_ref: float,
    voltage: float,
    ref_voltage: float = 6.0,
    n_motors: int = 2,
    c_rr: float = 0.02,
) -> float:
    """
    Calculate the maximum loaded speed of a robot in kilometers per hour (km/h).

    Parameters:
        mass_kg: Mass of the robot in kilograms.
        wheel_diameter_mm: Diameter of the wheel in millimeters.
        stall_torque_kgcm: Stall torque for a single motor in kg·cm.
        rpm_no_load_ref: No-load rotational speed (in rpm) at the reference voltage.
        voltage: Actual electrical supply voltage in volts.
        ref_voltage: Reference voltage for the rpm_no_load_ref value.
        n_motors: Number of motors driving the wheels.
        c_rr: Coefficient of rolling resistance (typical value for rubber on a smooth floor is 0.02).

    Returns:
        Maximum speed of the loaded robot in kilometers per hour (km/h).
        Returns 0.0 if the load torque exceeds the available stall torque.
    """

    rpm_no_load = rpm_no_load_ref * voltage / ref_voltage
    omega_0 = rpm_no_load * 2 * pi / 60  # Convert rpm to rad/s

    stall_torque_nm_one = stall_torque_kgcm * 0.0980665  # 1 kg·cm = 0.0980665 N·m
    stall_torque_total = stall_torque_nm_one * n_motors

    r = (wheel_diameter_mm / MM_IN_M) / 2

    f_rr = mass_kg * G * c_rr  # rolling resistance force in Newtons
    load_torque = f_rr * r  # torque required to overcome rolling resistance

    if load_torque >= stall_torque_total:
        return 0.0

    omega_term = omega_0 * (1 - load_torque / stall_torque_total)

    v_ms = omega_term * r  # linear speed in m/s
    return v_ms * SEC_IN_H / 1000
