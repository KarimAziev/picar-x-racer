from typing import TYPE_CHECKING, Any, Dict, Iterator, Literal, Tuple, Union, cast

from app.core.px_logger import Logger
from app.exceptions.settings import InvalidSettings, UnchangedSettings
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.schemas.robot.motors import I2CDCMotorConfig
from app.schemas.robot.pwm import PWMDriverConfig
from app.schemas.robot.servos import AngularServoConfig, GPIOAngularServoConfig
from app.util.diff import recursive_diff
from pydantic import ValidationError

if TYPE_CHECKING:
    from app.adapters.picarx_adapter import PicarxAdapter
    from app.managers.file_management.json_data_manager import JsonDataManager
    from robot_hat import ServoService

_log = Logger(__name__, app_name="px_robot")


class SettingsService:
    _PICARX_CONFIG_FIELDS = frozenset(
        {
            "steering_servo",
            "cam_tilt_servo",
            "cam_pan_servo",
            "motors",
        }
    )

    def __init__(
        self,
        picarx: "PicarxAdapter",
        config_manager: "JsonDataManager",
        servo_field_names=[
            "steering_servo",
            "cam_tilt_servo",
            "cam_pan_servo",
        ],
    ) -> None:
        self.px = picarx
        self.config_manager = config_manager
        self.saved_settings = HardwareConfig(**self.config_manager.load_data())
        self._servo_field_names = servo_field_names

        self.config_manager.on(self.config_manager.UPDATE_EVENT, self.refresh_config)
        self.config_manager.on(self.config_manager.LOAD_EVENT, self.refresh_config)

    def refresh_config(self, data: Dict[str, Any]) -> None:
        self.saved_settings = HardwareConfig(**data)

    def merge_settings(self, data: PartialHardwareConfig) -> PartialHardwareConfig:
        data_dict = self._model_json_dump(data, exclude_unset=True)
        _log.info("Merging hardware settings: %s", data_dict)
        updated_keys = set(data_dict)
        if not updated_keys:
            raise UnchangedSettings("No data to update")

        try:
            candidate = HardwareConfig(
                **self._merge_nested_dicts(
                    self._model_json_dump(self.saved_settings),
                    data_dict,
                )
            )
        except ValidationError as err:
            raise InvalidSettings(f"Unable to merge hardware settings: {err}") from err
        self._validate_shared_pwm_drivers(candidate)

        _log.info("Applying data: %s", data_dict)

        saved_dict = self._activate_and_persist(
            candidate,
            activate_hardware=bool(updated_keys & self._PICARX_CONFIG_FIELDS),
        )
        partial_saved_dict = {k: saved_dict.get(k) for k in updated_keys}
        _log.info("Partially saved settings: %s", partial_saved_dict)

        return PartialHardwareConfig(**cast(Dict, partial_saved_dict))

    def save_settings(self, data: HardwareConfig) -> HardwareConfig:
        self._validate_shared_pwm_drivers(data)
        data_dict = self._model_json_dump(data)
        current_data = self._model_json_dump(self.saved_settings)
        lines = recursive_diff(data_dict, current_data)
        if lines:
            _log.info("Saving settings changed:\n" + "\n".join(lines))
        else:
            _log.warning("Saving setting without changes")
        hardware_changed = any(
            getattr(data, field_name) != getattr(self.saved_settings, field_name)
            for field_name in self._PICARX_CONFIG_FIELDS
        )
        saved_dict = self._activate_and_persist(
            data,
            activate_hardware=hardware_changed,
        )

        return HardwareConfig(**saved_dict)

    def _activate_and_persist(
        self,
        config: HardwareConfig,
        *,
        activate_hardware: bool,
    ) -> Dict[str, Any]:
        if not activate_hardware:
            return self.config_manager.update(self._model_json_dump(config))

        previous_config = self.px.config.model_copy(deep=True)
        self.px.cleanup()

        try:
            self.px.init_hardware(config=config, strict=True)
        except Exception as err:
            self._restore_hardware(previous_config)
            raise InvalidSettings(f"Unable to apply hardware settings: {err}") from err

        try:
            return self.config_manager.update(self._model_json_dump(config))
        except Exception:
            self._restore_hardware(previous_config)
            raise

    def _restore_hardware(self, config: HardwareConfig) -> None:
        _log.warning("Restoring the previous hardware configuration")
        self.px.cleanup()
        try:
            self.px.init_hardware(config=config)
        except Exception:
            _log.error(
                "Unable to restore the previous hardware configuration",
                exc_info=True,
            )

    @classmethod
    def _merge_nested_dicts(
        cls,
        existing: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge object fields recursively while replacing arrays and scalars."""

        merged = dict(existing)
        for key, value in updates.items():
            existing_value = merged.get(key)
            if isinstance(existing_value, dict) and isinstance(value, dict):
                merged[key] = cls._merge_nested_dicts(existing_value, value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _iter_pwm_driver_configs(
        config: HardwareConfig,
    ) -> Iterator[Tuple[str, PWMDriverConfig]]:
        for servo_name in (
            "cam_pan_servo",
            "cam_tilt_servo",
            "steering_servo",
        ):
            servo = getattr(config, servo_name)
            if isinstance(servo, AngularServoConfig) and servo.enabled:
                yield servo_name, servo.driver

        for index, motor in enumerate(config.motors):
            if isinstance(motor, I2CDCMotorConfig) and motor.enabled:
                yield f"motors[{index}]", motor.driver

    @classmethod
    def _validate_shared_pwm_drivers(cls, config: HardwareConfig) -> None:
        drivers: Dict[Tuple[int, int], Tuple[str, PWMDriverConfig]] = {}
        for consumer, driver_config in cls._iter_pwm_driver_configs(config):
            existing = drivers.get(driver_config.hardware_key)
            if existing is None:
                drivers[driver_config.hardware_key] = (consumer, driver_config)
                continue

            existing_consumer, existing_config = existing
            if existing_config.hardware_signature == driver_config.hardware_signature:
                continue

            raise InvalidSettings(
                "Conflicting configurations for shared PWM device on "
                f"bus {driver_config.bus}, address {driver_config.addr_str}: "
                f"{existing_consumer} uses {existing_config.name} "
                f"({existing_config.freq} Hz, frame width "
                f"{existing_config.frame_width} us), while {consumer} uses "
                f"{driver_config.name} ({driver_config.freq} Hz, frame width "
                f"{driver_config.frame_width} us). All enabled consumers of one "
                "physical PWM device must use the same driver configuration."
            )

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
        return data.model_dump(
            mode="json",
            exclude={
                **excluded_servo_data,
                "motors": {"__all__": {"saved_calibration_direction"}},
            },
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
            active_configs = [motor for motor in config.motors if motor.enabled]
            for motor, motor_config in zip(self.px.motors, active_configs):
                motor_config.calibration_direction = motor.direction

        return config
