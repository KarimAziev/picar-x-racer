from functools import lru_cache
from typing import TYPE_CHECKING, List, cast

from app.core.px_logger import Logger
from app.exceptions.pin import PinFactoryNotAvailable
from app.schemas.robot.pin import BoardInfoModel, DeviceInfo, PinsHeader

if TYPE_CHECKING:
    from gpiozero import HeaderInfo

_log = Logger(name=__name__)


class PinService:
    @staticmethod
    @lru_cache()
    def device_info() -> DeviceInfo:
        from gpiozero import Device

        Device.ensure_pin_factory()
        if not Device.pin_factory:
            err = "Pin factory is not available!"
            _log.error(err)
            raise PinFactoryNotAvailable(err)

        header_info_vals: List[HeaderInfo] = (
            Device.pin_factory.board_info.headers.values()
        )

        headers = {
            cast(str, header.name): PinsHeader.from_header_info(header)
            for header in header_info_vals
        }

        board_info = BoardInfoModel.from_board_info(Device.pin_factory.board_info)

        return DeviceInfo(board=board_info, headers=headers)


if __name__ == "__main__":
    from pprint import pp

    from app.util.setup_env import setup_env_vars

    setup_env_vars()

    device_info = PinService.device_info()
    print(f"Device Info")
    print("")
    pp(device_info.model_dump())
