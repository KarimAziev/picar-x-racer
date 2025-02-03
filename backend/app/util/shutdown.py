from app.core.logger import Logger

logger = Logger(__name__)


def power_off():
    """
    Trigger a system shutdown using the systemd D-Bus interface.

    [!CAUTION]
    --------------
    Ensure that this function is only called when a shutdown is intended, as
    it will terminate all running processes and power off the host machine
    immediately.

    This function sends a `PowerOff` request to the systemd login manager via
    D-Bus. It is designed for use cases where the system must be powered off
    gracefully.


    Raises:
        Exception: If the D-Bus interface is unavailable or the PowerOff request fails.
    """
    import dbus

    try:
        bus = dbus.SystemBus()

        systemd = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
        manager = dbus.Interface(systemd, "org.freedesktop.login1.Manager")
        logger.warning("Shutdown initiated via dbus")
        manager.PowerOff(True)
    except Exception:
        logger.error("Failed to shutdown machine via dbus", exc_info=True)
        raise


def restart():
    """
        Trigger a system restart using the systemd D-Bus interface.

    [!CAUTION]
    --------------
    Ensure that this function is only called when a restart is intended, as
    it will terminate all running processes and reboot the host machine
    immediately.

    This function sends a `Reboot` request to the systemd login manager via
    D-Bus. It is designed for use cases where the system must be rebooted
    gracefully.

    Raises:
        Exception: If the D-Bus interface is unavailable or the Reboot request fails.
    """
    import dbus

    try:
        bus = dbus.SystemBus()

        systemd = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
        manager = dbus.Interface(systemd, "org.freedesktop.login1.Manager")
        logger.warning("Restart initiated via dbus")
        manager.Reboot(True)
    except Exception:
        logger.error("Failed to restart machine via dbus", exc_info=True)
        raise
