"""GPIO reservations for services that run in separate processes."""

from typing import Iterator, Union

from gpiozero.pins.pi import PiBoardInfo

from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.localization_sensors import GPIOQuadratureEncoderConfig
from app.schemas.robot.motors import GPIODCMotorConfig, I2CDCMotorConfig
from app.schemas.robot.servos import GPIOAngularServoConfig
from robot_hat import Pin


# The 40-pin header mapping is shared by Pi 3, Pi 4, and Pi 5. Supplying
# a revision keeps validation independent of the host and GPIO backend.
_HEADER = PiBoardInfo.from_revision(0xA02082)


def gpio_number(pin: Union[int, str]) -> int:
    """Resolve robot-hat and gpiozero aliases without claiming an output."""
    if isinstance(pin, str):
        pin = Pin.DEFAULT_PIN_MAPPING.get(pin, pin)
    return int(_HEADER.to_gpio(pin).removeprefix("GPIO"))


def hardware_gpio_pins(
    config: HardwareConfig,
) -> Iterator[tuple[str, Union[int, str]]]:
    """Reserve wired actuator pins even when their software control is disabled."""
    for index, motor in enumerate(config.motors):
        prefix = f"motors[{index}]"
        if isinstance(motor, GPIODCMotorConfig):
            yield f"{prefix}.forward_pin", motor.forward_pin
            yield f"{prefix}.backward_pin", motor.backward_pin
            if motor.enable_pin is not None:
                yield f"{prefix}.enable_pin", motor.enable_pin
        elif isinstance(motor, I2CDCMotorConfig):
            yield f"{prefix}.dir_pin", motor.dir_pin
        else:
            yield f"{prefix}.phase_pin", motor.phase_pin
            yield f"{prefix}.enable_pin", motor.enable_pin
    for name in ("steering_servo", "cam_pan_servo", "cam_tilt_servo"):
        servo = getattr(config, name)
        if isinstance(servo, GPIOAngularServoConfig):
            yield f"{name}.pin", servo.pin
    if config.ultrasonic:
        yield "ultrasonic.trig_pin", config.ultrasonic.trig_pin
        yield "ultrasonic.echo_pin", config.ultrasonic.echo_pin
    for index, sensor in enumerate(config.localization_sensors.encoder.sensors):
        if isinstance(sensor, GPIOQuadratureEncoderConfig):
            yield f"encoder.sensors[{index}].a_pin", sensor.a_pin
            yield f"encoder.sensors[{index}].b_pin", sensor.b_pin


def validate_led_pin(config: HardwareConfig, pin: Union[int, str]) -> None:
    """Reject an LED output that could drive another wired device."""
    number = gpio_number(pin)
    for owner, other_pin in hardware_gpio_pins(config):
        if number == gpio_number(other_pin):
            raise ValueError(
                f"LED GPIO{number} is reserved by {owner}; "
                "choose an unused GPIO or set led to null"
            )


def validate_distance_pins(config: HardwareConfig) -> None:
    """Reject ultrasonic GPIOs that could drive a wired actuator or encoder."""
    if config.ultrasonic is None:
        return
    pins = (config.ultrasonic.trig_pin, config.ultrasonic.echo_pin)
    if gpio_number(pins[0]) == gpio_number(pins[1]):
        raise ValueError("Ultrasonic trigger and echo must use different GPIOs")
    for pin in pins:
        number = gpio_number(pin)
        for owner, other_pin in hardware_gpio_pins(config):
            if not owner.startswith("ultrasonic.") and number == gpio_number(other_pin):
                raise ValueError(f"Ultrasonic GPIO{number} is reserved by {owner}")
