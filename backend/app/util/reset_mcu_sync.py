import time


def reset_mcu_sync():
    """
    Resets the MCU (Microcontroller Unit) by toggling the state of the MCU reset pin.

    This function uses the robot hat adapter's Pin interface to manipulate the "MCURST"
    pin. The reset process is handled by briefly pulling the reset pin low (off),
    waiting for 10 milliseconds, and then pulling it high (on) again, followed by
    another short delay. Finally, the pin resource is released or closed.

    Steps:
      1. Instantiate the `MCURST` Pin object.
      2. Set the pin to the OFF state (low) to reset the MCU.
      3. Wait for 10 milliseconds.
      4. Set the pin to the ON state (high) to complete the reset.
      5. Wait for another 10 milliseconds.
      6. Close the Pin instance to release resources.

    This function is synchronous and blocks execution while the delays occur.

    Example:
      reset_mcu_sync()
    """
    from app.adapters.robot_hat.pin import Pin

    mcu_reset = Pin("MCURST")
    mcu_reset.off()
    time.sleep(0.01)
    mcu_reset.on()
    time.sleep(0.01)

    mcu_reset.close()


if __name__ == "main":
    reset_mcu_sync()
