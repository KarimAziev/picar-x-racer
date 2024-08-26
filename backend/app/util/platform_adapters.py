from app.util.os_checks import is_raspberry_pi

is_os_raspberry = is_raspberry_pi()

if is_os_raspberry:
    from app.modules.picarx import Picarx
    from app.modules.vilib import Vilib
    from robot_hat import Music
    from robot_hat.utils import (
        reset_mcu,
        get_ip,
        set_volume,
        run_command,
        is_installed,
        mapping,
        get_battery_voltage,
    )
else:
    from app.mock.picarx import Picarx
    from app.modules.vilib import Vilib
    from app.mock.music import Music
    from app.mock.robot_hat_fake_utils import (
        reset_mcu,
        get_ip,
        set_volume,
        run_command,
        is_installed,
        mapping,
        get_battery_voltage,
    )


Picarx = Picarx
Vilib = Vilib
Music = Music
reset_mcu = reset_mcu
get_ip = get_ip
set_volume = set_volume
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
    "set_volume",
    "run_command",
    "is_installed",
    "mapping",
    "get_battery_voltage",
]
