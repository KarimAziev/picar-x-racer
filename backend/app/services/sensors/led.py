from time import sleep

from gpiozero import LED

led = LED(26)

try:
    while True:
        led.on()
        sleep(1)
        led.off()
        sleep(1)
except KeyboardInterrupt:
    print("Ending program")
except Exception as e:
    print(f"Unhandled exception: {e}")
finally:
    led.off()
