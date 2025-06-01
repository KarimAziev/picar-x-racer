from typing import Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class LedConfig(BaseModel):
    """
    The configuration for the single LED.
    """

    name: Annotated[
        str,
        Field(
            ...,
            description="Human-readable name",
            examples=["LED"],
        ),
    ] = "LED"

    interval: Annotated[
        float,
        Field(
            default=0.1,
            ge=0,
            description="The interval of LED blinking.",
            json_schema_extra={
                "props": {
                    "step": 0.1,
                    "minFractionDigits": 0,
                    "maxFractionDigits": 6,
                    "placeholder": "Interval (in seconds)",
                },
            },
            examples=[
                0.1,
            ],
        ),
    ]

    pin: Annotated[
        Union[str, int],
        Field(
            default=26,
            json_schema_extra={"type": "string_or_number"},
            description="The GPIO pin number for the LED.",
            examples=[26],
        ),
    ]


if __name__ == "__main__":
    from pprint import pp

    print("\n\033[1m\033[32m Led Config \033[0m\033[36mJSON schema:\033[0m")
    pp(LedConfig.model_json_schema())
