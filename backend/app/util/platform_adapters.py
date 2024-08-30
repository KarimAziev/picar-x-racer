from app.util.os_checks import is_raspberry_pi
from app.modules.vilib import Vilib
from app.modules.music import Music

is_os_raspberry = is_raspberry_pi()

if is_os_raspberry:
    from app.modules.picarx import Picarx
    from robot_hat.utils import (
        reset_mcu,
        get_ip,
        run_command,
        is_installed,
        mapping,
        get_battery_voltage,
    )
else:
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

__all__ = [
    "Picarx",
    "Vilib",
    "Music",
    "reset_mcu",
    "get_ip",
    "run_command",
    "is_installed",
    "mapping",
    "get_battery_voltage",
]
