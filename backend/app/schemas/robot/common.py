import re
from typing import Union

from app.core.logger import Logger
from pydantic import BaseModel, Field, computed_field, field_validator
from typing_extensions import Annotated

logger = Logger(__name__)

EnabledField = Annotated[
    bool,
    Field(
        ...,
        title="Enabled",
        description="Whether the device or sensor is enabled.",
    ),
]

AddressField = Annotated[
    Union[int, str],
    Field(
        ...,
        title="I2C address",
        description="I2C address of the device",
        examples=[0x40, "0x40", 64],
        json_schema_extra={"type": "hex"},
    ),
]


class AddressModel(BaseModel):
    address: AddressField

    @field_validator("address", mode="before")
    def parse_hex_address(cls, value):
        if isinstance(value, str):
            if not re.fullmatch(r"0[xX][0-9a-fA-F]+", value):
                raise ValueError(
                    "Address string must be a valid hexadecimal (e.g., '0x40')."
                )

            int_val = int(value, 16)
        else:
            int_val = value

        if int_val < 0:
            raise ValueError("Address must be a positive number.")

        return value

    @computed_field
    @property
    def addr_str(self) -> str:
        if isinstance(self.address, int):
            return hex(self.address)
        return self.address

    @computed_field
    @property
    def addr_int(self) -> int:
        if isinstance(self.address, int):
            return self.address
        return int(self.address, 16)


if __name__ == "__main__":
    from pprint import pp

    print("\n\033[1m\033[32m Address Model \033[0m\033[36mJSON schema:\033[0m")
    pp(AddressModel.model_json_schema())
