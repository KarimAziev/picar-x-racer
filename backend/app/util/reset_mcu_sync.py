import time

from app.adapters.robot_hat.pin import Pin


def reset_mcu_sync():
    mcu_reset = Pin("MCURST")
    mcu_reset.off()
    time.sleep(0.01)
    mcu_reset.on()
    time.sleep(0.01)

    mcu_reset.close()
