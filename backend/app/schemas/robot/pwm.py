from typing import Literal

from app.schemas.robot.common import AddressField, AddressModel, IC2Bus
from pydantic import Field
from robot_hat.data_types.config.pwm import PWMDriverConfig as PWMDriverConfigDataclass
from typing_extensions import Annotated


class PWMDriverConfig(AddressModel):
    """
    The configuration parameters to control a PWM driver chip via the I2C bus.
    """

    name: Annotated[
        Literal["PCA9685", "Sunfounder"],
        Field(
            ...,
            description="Model of the PWM driver chip",
            examples=["Sunfounder", "PCA9685"],
            json_schema_extra={
                "type": "select",
                "props": {
                    "options": [
                        {"value": "PCA9685", "label": "PCA9685"},
                        {"value": "Sunfounder", "label": "Sunfounder"},
                    ]
                },
            },
        ),
    ] = "PCA9685"

    bus: IC2Bus = 1
    frame_width: Annotated[
        int,
        Field(
            ...,
            title="Frame Width in µs",
            description="Determines the full cycle duration between servo control pulses in microseconds. "
            "This value represents the period in which all servo channels are refreshed. "
            "A typical servo expects a pulse every 20000 µs (20 ms), and altering this value can affect "
            "the overall responsiveness and timing sensitivity of the servo's control signal.",
            examples=[20000],
            ge=1,
        ),
    ] = 20000
    freq: Annotated[
        int,
        Field(
            ...,
            title="PWM frequency (Hz)",
            description="The PWM frequency in Hertz which controls the granularity of the pulse width modulation. "
            "Higher frequencies allow for more precise adjustments of the pulse width (duty cycle), "
            "resulting in smoother and more accurate servo movements. Conversely, lower frequencies might lead "
            "to coarser control.",
            examples=[50],
            gt=0,
        ),
    ] = 50

    address: AddressField = "0x40"

    def to_dataclass(self) -> PWMDriverConfigDataclass:
        return PWMDriverConfigDataclass(
            address=self.addr_int,
            name=self.name,
            bus=self.bus,
            frame_width=self.frame_width,
            freq=self.freq,
        )


if __name__ == "__main__":
    from pprint import pp

    print("\n\033[1m\033[32m PWM Driver Config \033[0m\033[36mJSON schema:\033[0m")
    pp(PWMDriverConfig.model_json_schema())
