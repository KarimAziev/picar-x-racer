from typing import TYPE_CHECKING, Dict, List, Optional

from app.core.logger import Logger
from pydantic import BaseModel, Field
from typing_extensions import Annotated, Self

logger = Logger(__name__)

if TYPE_CHECKING:
    from gpiozero import BoardInfo, HeaderInfo, PinInfo


class Pin(BaseModel):
    """
    The model representing Pin info.
    """

    name: Annotated[
        str,
        Field(
            ...,
            title="Name",
            description="Pin Name",
            examples=["GPIO17", "GND", "TR00 TAP", "RUN"],
        ),
    ]

    number: Annotated[
        int,
        Field(
            ...,
            title="Name",
            description="An integer containing the physical pin number on the header (starting from 1 in accordance with convention).",
            examples=[1, 2, 3, 4],
        ),
    ]

    gpio_number: Annotated[
        Optional[int],
        Field(
            ...,
            title="Name",
            description="GPIO number if any",
            examples=[17, 27],
        ),
    ]

    row: Annotated[
        int,
        Field(
            ...,
            title="Row number",
            description="An integer indicating on which row the pin is physically located in the header (1-based)",
            examples=[1, 2, 3, 4],
        ),
    ]

    col: Annotated[
        int,
        Field(
            ...,
            title="Column number",
            description="An integer indicating in which column the pin is physically located in the header (1-based)",
            examples=[1, 2],
        ),
    ]

    names: Annotated[
        list[str],
        Field(
            ...,
            title="Names",
            description="All the names that can be used to identify this pin.",
            examples=["BCM17", "BOARD11", "GPIO17", "J8:11", "WPI0"],
        ),
    ]

    interfaces: Annotated[
        list[str],
        Field(
            ...,
            title="Interfaces",
            description="Mapping interfaces that the pin can be a part of.",
            examples=["dpi", "gpio", "spi", "uart"],
        ),
    ]

    @classmethod
    def from_pin_info(cls, pin_info: "PinInfo") -> Self:

        gpio_number: Optional[int] = None

        str_names: List[str] = []

        for name in pin_info.names:
            if isinstance(name, str) and not name.isdigit():
                str_names.append(name)
            elif isinstance(name, int):
                gpio_number = name

        if gpio_number is not None:
            from robot_hat import Pin

            extra_mapping = Pin.DEFAULT_PIN_MAPPING
            aliases = [key for key, val in extra_mapping.items() if gpio_number == val]
            if aliases:
                str_names.extend(aliases)

        return cls(
            name=pin_info.name,
            number=pin_info.number,
            gpio_number=gpio_number,
            names=str_names,
            row=pin_info.row,
            col=pin_info.col,
            interfaces=[
                item
                for item in pin_info.interfaces
                if item != "" and isinstance(item, str)
            ],
        )


class PinsHeader(BaseModel):
    """
    The model representing Pin header.
    """

    name: Annotated[
        str,
        Field(
            ...,
            title="Name",
            description="The name of the header, typically as it appears silk-screened on the board.",
            examples=["J8", "P1"],
        ),
    ]

    rows: Annotated[
        int,
        Field(
            ...,
            title="Rows",
            description="The number of rows on the header.",
            examples=[1, 2, 3, 4],
        ),
    ]

    columns: Annotated[
        int,
        Field(
            ...,
            title="Column number",
            description="The number of columns on the header.",
            examples=[1, 2],
        ),
    ]

    pins: Annotated[
        Dict[int, Pin],
        Field(
            ...,
            title="Columns",
            description="A dictionary mapping physical pin numbers.",
        ),
    ]

    @classmethod
    def from_header_info(cls, header_info: "HeaderInfo") -> Self:
        pins_vals: List["PinInfo"] = header_info.pins.values()
        mapped_pins = {v.number: Pin.from_pin_info(v) for v in pins_vals}
        return cls(
            name=header_info.name,
            rows=header_info.rows,
            columns=header_info.columns,
            pins=mapped_pins,
        )


class BoardInfoModel(BaseModel):
    model: Annotated[
        str,
        Field(
            ...,
            title="Model",
            description="A string containing the model of the board.",
            examples=["B", "B+", "A+", "2B", "CM", "Zero"],
        ),
    ]

    revision: Annotated[
        str,
        Field(
            ...,
            title="Revision",
            description="A string indicating the revision of the board (unique identifier for the revision).",
            examples=["e04171"],
        ),
    ]

    pcb_revision: Annotated[
        str,
        Field(
            ...,
            title="PCB revision",
            description="A string containing the PCB revision number which is silk-screened onto the board.",
            examples=["1.1"],
        ),
    ]

    released: Annotated[
        str,
        Field(
            ...,
            title="Approximate release date",
            description="A string containing an approximate release date for this board (formatted as yyyyQq, e.g. 2012Q1).",
            examples=["2023Q4", "2012Q1"],
        ),
    ]

    soc: Annotated[
        str,
        Field(
            ...,
            title="SoC",
            description="A string indicating the SoC (system on a chip) that powers this board.",
            examples=["BCM2712", "BCM2837"],
        ),
    ]

    manufacturer: Annotated[
        str,
        Field(
            ...,
            title="Manufacturer",
            description="A string indicating the name of the manufacturer.",
            examples=["Sony", "Raspberry Pi Foundation"],
        ),
    ]

    memory: Annotated[
        int,
        Field(
            ...,
            title="Memory (Mb)",
            description="An integer indicating the amount of memory (in Mb) connected to the SoC.",
            ge=0,
            examples=[256, 1024, 16384],
        ),
    ]

    storage: Annotated[
        str,
        Field(
            ...,
            title="Typical storage",
            description='A string indicating the typical bootable storage used with this board (e.g. "SD", "MicroSD", or "eMMC").',
            examples=["MicroSD", "SD", "eMMC"],
        ),
    ]

    usb: Annotated[
        int,
        Field(
            ...,
            title="USB ports",
            description="An integer indicating how many USB ports are physically present on this board (any type).",
            ge=0,
            examples=[0, 1, 2, 4],
        ),
    ]

    usb3: Annotated[
        int,
        Field(
            ...,
            title="USB3 ports",
            description="An integer indicating how many of the USB ports are USB3 ports on this board.",
            ge=0,
            examples=[0, 1, 2],
        ),
    ]

    ethernet: Annotated[
        int,
        Field(
            ...,
            title="Ethernet ports",
            description="An integer indicating how many Ethernet ports are physically present on this board.",
            ge=0,
            examples=[0, 1, 2],
        ),
    ]

    eth_speed: Annotated[
        int,
        Field(
            ...,
            title="Ethernet speed (Mbps)",
            description="An integer indicating the maximum speed (in Mbps) of the Ethernet ports (0 if none).",
            ge=0,
            examples=[0, 100, 1000],
        ),
    ]

    wifi: Annotated[
        bool,
        Field(
            ...,
            title="WiFi",
            description="A bool indicating whether this board has WiFi built-in.",
            examples=[True, False],
        ),
    ]

    bluetooth: Annotated[
        bool,
        Field(
            ...,
            title="Bluetooth",
            description="A bool indicating whether this board has Bluetooth built-in.",
            examples=[True, False],
        ),
    ]

    csi: Annotated[
        int,
        Field(
            ...,
            title="CSI ports",
            description="An integer indicating the number of CSI (camera) ports available on this board.",
            ge=0,
            examples=[0, 1, 2],
        ),
    ]

    dsi: Annotated[
        int,
        Field(
            ...,
            title="DSI ports",
            description="An integer indicating the number of DSI (display) ports available on this board.",
            ge=0,
            examples=[0, 1, 2],
        ),
    ]

    @classmethod
    def from_board_info(cls, board_info: "BoardInfo") -> Self:
        return cls(
            model=board_info.model,
            bluetooth=board_info.bluetooth,
            csi=board_info.csi,
            dsi=board_info.dsi,
            eth_speed=board_info.eth_speed,
            ethernet=board_info.ethernet,
            manufacturer=board_info.manufacturer,
            memory=board_info.memory,
            pcb_revision=board_info.pcb_revision,
            released=board_info.released,
            revision=board_info.revision,
            soc=board_info.soc,
            storage=board_info.storage,
            usb=board_info.usb,
            usb3=board_info.usb3,
            wifi=board_info.wifi,
        )


class DeviceInfo(BaseModel):
    board: BoardInfoModel
    headers: Dict[str, PinsHeader]
