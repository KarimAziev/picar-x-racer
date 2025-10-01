from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union, cast

from app.core.px_logger import Logger
from app.exceptions.settings import UnchangedSettings
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.schemas.robot.motors import (
    GPIODCMotorConfig,
    I2CDCMotorConfig,
    PhaseMotorConfig,
)
from app.schemas.robot.servos import AngularServoConfig, GPIOAngularServoConfig
from app.util.diff import recursive_diff
from robot_hat.interfaces.motor_abc import MotorABC

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.managers.file_management.json_data_manager import JsonDataManager
    from robot_hat import ServoService

_log = Logger(__name__, app_name="px_robot")


class SettingsService:
    def __init__(
        self,
        picarx: "PicarxAdapter",
        config_manager: "JsonDataManager",
        servo_field_names=[
            "steering_servo",
            "cam_tilt_servo",
            "cam_pan_servo",
        ],
        motor_field_names=[
            "left_motor",
            "right_motor",
        ],
    ) -> None:
        self.px = picarx
        self.config_manager = config_manager
        self.saved_settings = HardwareConfig(**self.config_manager.load_data())
        self._servo_field_names = servo_field_names
        self._motor_field_names = motor_field_names

        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.refresh_config)
        self.config_manager.on(self.config_manager.LOAD_EVENT, self.refresh_config)

    def refresh_config(self, data: Dict[str, Any]) -> None:
        self.saved_settings = HardwareConfig(**data)

    def merge_settings(self, data: PartialHardwareConfig) -> PartialHardwareConfig:
        data_dict = self._model_json_dump(data, exclude_unset=True)
        _log.info("Merging hardware settings: %s", data_dict)
        updated_keys = data_dict.keys()
        if not updated_keys:
            raise UnchangedSettings("No data to update")

        _log.info("Saving data: %s", data_dict)

        saved_dict = self.config_manager.merge(data_dict)
        partial_saved_dict = {k: saved_dict.get(k) for k in updated_keys}
        _log.info("Partially saved settings: %s", partial_saved_dict)
        config = HardwareConfig(**{**self.px.config.model_dump(), **partial_saved_dict})

        self.px.config = config
        self.px.cleanup()
        self.px.init_hardware()

        return PartialHardwareConfig(**cast(Dict, partial_saved_dict))

    def save_settings(self, data: HardwareConfig) -> HardwareConfig:
        data_dict = self._model_json_dump(data)
        current_data = self._model_json_dump(self.saved_settings)
        lines = recursive_diff(data_dict, current_data)
        if lines:
            _log.info("Saving settings changed:\n" + "\n".join(lines))
        else:
            _log.warning("Saving setting without changes")
        config = HardwareConfig(**self.config_manager.update(data_dict))
        self.px.config = config
        self.px.cleanup()
        self.px.init_hardware()

        return self.px.config

    def _model_json_dump(
        self,
        data: HardwareConfig,
        context: Union[Any, None] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: Union[bool, Literal["none", "warn", "error"]] = True,
        serialize_as_any: bool = False,
    ) -> Dict[str, Any]:
        excluded_servo_data = {
            k: {"saved_calibration_offset"} for k in self._servo_field_names
        }
        excluded_motors_data = {
            k: {"saved_calibration_direction"} for k in self._motor_field_names
        }
        return data.model_dump(
            mode="json",
            exclude={**excluded_servo_data, **excluded_motors_data},
            context=context,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            by_alias=by_alias,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    def get_saved_settings(self) -> HardwareConfig:
        return self.saved_settings

    def get_current_settings(self) -> HardwareConfig:
        config = HardwareConfig(**self.config_manager.load_data())
        for servo_name in self._servo_field_names:
            servo: "ServoService" = getattr(self.px, servo_name)
            servo_config: Union[GPIOAngularServoConfig, AngularServoConfig, None] = (
                getattr(config, servo_name)
            )

            if servo and servo_config:
                servo_config.calibration_offset = servo.calibration_offset

        if self.px.motor_controller:
            for motor_name in self._motor_field_names:
                motor: Optional["MotorABC"] = getattr(self.px, motor_name)

                motor_config: Union[
                    PhaseMotorConfig, GPIODCMotorConfig, I2CDCMotorConfig, None
                ] = getattr(config, motor_name)
                if motor and motor_config:
                    motor_config.calibration_direction = motor.direction

        return config
