import math
from functools import lru_cache
from typing import Annotated, AsyncGenerator, Dict, Optional, TypedDict

from app.adapters.picarx_adapter import PicarxAdapter
from app.config.config import settings as app_config
from app.core.async_emitter import AsyncEventEmitter
from app.core.logger import Logger
from app.managers.async_task_manager import AsyncTaskManager
from app.managers.file_management.json_data_manager import JsonDataManager
from app.migrations.robot_config import create_robot_config_migrator
from app.schemas.robot.config import HardwareConfig
from app.schemas.autonomy import SensorName
from app.services.connection_service import ConnectionService
from app.services.autonomy import (
    AckermannOdometryConfig,
    AckermannOdometryEstimator,
    AckermannOdometryService,
    ActuationCalibration,
    HardwareController,
    LinearActuatorTranslator,
    LaserScanConverter,
    LidarSafetyEvaluator,
    LidarSafetyService,
    LidarSafetyZone,
    LocalMappingService,
    LocalOccupancyGrid,
    LocalOccupancyGridConfig,
    LidarPublisherService,
    LocalizationSensorService,
    IMUPublisherService,
    MotionArbiter,
    MotionControlService,
    MotionLimits,
    TopicBus,
    UnavailableEncoderPublisher,
    StaticTransform2D,
)
from app.services.autonomy.sensor_publishers import SensorPublisher
from app.services.control.calibration_service import CalibrationService
from app.services.control.car_service import CarService
from app.services.control.settings_service import SettingsService
from app.services.sensors.distance_service import DistanceService
from app.services.sensors.led_service import LEDService
from app.services.sensors.pinout_service import PinoutService
from app.services.sensors.speed_estimator import SpeedEstimator
from fastapi import Depends
from robot_hat.i2c.smbus_manager import SMBusManager
from robot_hat import RPLidarC1, RPLidarC1Config, SH3001, SH3001Config

logger = Logger(__name__)


@lru_cache()
def get_connection_manager() -> ConnectionService:
    """Return connection manager used for broadcasting."""
    return ConnectionService(
        app_name="px_robot", log_prefix="Robot Connection Manager: "
    )


@lru_cache()
def get_async_event_emitter() -> AsyncEventEmitter:
    return AsyncEventEmitter()


@lru_cache()
def get_async_task_manager() -> AsyncTaskManager:
    return AsyncTaskManager()


@lru_cache()
def get_robot_topic_bus() -> TopicBus:
    return TopicBus()


@lru_cache()
def get_config_manager() -> JsonDataManager:
    return JsonDataManager(
        target_file=app_config.ROBOT_CONFIG_FILE,
        template_file=app_config.DEFAULT_ROBOT_CONFIG_FILE,
        migrator=create_robot_config_migrator(),
    )


@lru_cache()
def get_app_settings_manager() -> JsonDataManager:
    return JsonDataManager(
        target_file=app_config.PX_SETTINGS_FILE,
        template_file=app_config.DEFAULT_USER_SETTINGS,
    )


@lru_cache()
def get_speed_estimator() -> SpeedEstimator:
    return SpeedEstimator()


@lru_cache(maxsize=1)
def get_distance_service(
    emitter: Annotated[AsyncEventEmitter, Depends(get_async_event_emitter)],
    task_manager: Annotated[AsyncTaskManager, Depends(get_async_task_manager)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
) -> DistanceService:
    return DistanceService(
        emitter=emitter, task_manager=task_manager, config_manager=config_manager
    )


@lru_cache()
def get_led_service(
    emitter: Annotated[AsyncEventEmitter, Depends(get_async_event_emitter)],
    task_manager: Annotated[AsyncTaskManager, Depends(get_async_task_manager)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
) -> LEDService:
    return LEDService(
        config_manager=config_manager, emitter=emitter, task_manager=task_manager
    )


@lru_cache()
def get_smbus_manager() -> SMBusManager:
    return SMBusManager()


@lru_cache(maxsize=1)
def get_picarx_adapter(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    smbus_manager: Annotated[SMBusManager, Depends(get_smbus_manager)],
) -> PicarxAdapter:
    return PicarxAdapter(config_manager=config_manager, smbus_manager=smbus_manager)


@lru_cache(maxsize=1)
def get_motion_control_service(
    picarx_adapter: Annotated[PicarxAdapter, Depends(get_picarx_adapter)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> Optional[MotionControlService]:
    """Build the opt-in single-writer motion runtime from calibrated config."""

    config = HardwareConfig.model_validate(config_manager.load_data())
    motion = config.motion_control
    if not motion.enabled:
        return None
    if motion.max_forward_speed_mps is None or motion.max_reverse_speed_mps is None:
        raise ValueError("Motion control is enabled without physical speed calibration")

    enabled_motors = [motor for motor in config.motors if motor.enabled]
    if not enabled_motors:
        raise ValueError("Motion control requires at least one enabled motor")
    max_motor_command = min(100, *(motor.max_speed for motor in enabled_motors))
    max_steering_degrees = min(
        abs(config.steering_servo.min_angle),
        abs(config.steering_servo.max_angle),
    )
    if max_steering_degrees <= 0:
        raise ValueError("Motion control requires a steering range around zero")

    max_steering_radians = math.radians(max_steering_degrees)
    limits = MotionLimits(
        max_forward_speed_mps=motion.max_forward_speed_mps,
        max_reverse_speed_mps=motion.max_reverse_speed_mps,
        max_abs_steering_angle_rad=max_steering_radians,
    )
    calibration = ActuationCalibration(
        max_forward_speed_mps=motion.max_forward_speed_mps,
        max_reverse_speed_mps=motion.max_reverse_speed_mps,
        max_abs_steering_angle_rad=max_steering_radians,
        max_forward_command=max_motor_command,
        max_reverse_command=max_motor_command,
    )
    return MotionControlService(
        arbiter=MotionArbiter(limits),
        hardware_controller=HardwareController(
            picarx_adapter,
            LinearActuatorTranslator(calibration),
        ),
        control_period_seconds=1.0 / motion.control_frequency_hz,
        topic_bus=topic_bus,
    )


@lru_cache(maxsize=1)
def get_odometry_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> Optional[AckermannOdometryService]:
    """Build odometry only after measured Ackermann geometry is enabled."""

    config = HardwareConfig.model_validate(config_manager.load_data())
    odometry = config.ackermann_odometry
    if not odometry.enabled:
        return None
    if odometry.wheelbase_m is None:
        raise ValueError("Ackermann odometry is enabled without wheelbase calibration")
    if odometry.wheel_radius_m is None:
        raise ValueError(
            "Ackermann odometry is enabled without wheel radius calibration"
        )
    if odometry.encoder_ticks_per_revolution is None:
        raise ValueError("Ackermann odometry is enabled without encoder calibration")
    return AckermannOdometryService(
        topic_bus,
        AckermannOdometryEstimator(
            AckermannOdometryConfig(
                wheelbase_m=odometry.wheelbase_m,
                wheel_radius_m=odometry.wheel_radius_m,
                encoder_ticks_per_revolution=(odometry.encoder_ticks_per_revolution),
                gear_ratio=odometry.gear_ratio,
                max_steering_age_seconds=odometry.max_steering_age_ms / 1000,
            )
        ),
    )


@lru_cache(maxsize=1)
def get_localization_sensor_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    smbus_manager: Annotated[SMBusManager, Depends(get_smbus_manager)],
) -> LocalizationSensorService:
    """Build lazy, opt-in hardware publishers from the persisted configuration."""

    config = HardwareConfig.model_validate(config_manager.load_data())
    sensors = config.localization_sensors
    publishers: Dict[SensorName, SensorPublisher] = {}
    enabled_sensors = []

    if sensors.lidar.enabled:
        enabled_sensors.append("lidar")
        range_min_m = sensors.lidar.range_min_m
        range_max_m = sensors.lidar.range_max_m
        if range_min_m is None or range_max_m is None:
            raise ValueError("enabled lidar requires calibrated range limits")
        lidar_config = RPLidarC1Config(
            port=sensors.lidar.port,
            baudrate=sensors.lidar.baudrate,
            timeout=sensors.lidar.timeout_s,
        )
        publishers["lidar"] = LidarPublisherService(
            topic_bus,
            lambda: RPLidarC1(lidar_config),
            LaserScanConverter(
                frame_id=sensors.lidar.frame_id,
                range_min_m=range_min_m,
                range_max_m=range_max_m,
                angular_resolution_deg=sensors.lidar.angular_resolution_deg,
            ),
            min_measurements_per_scan=(sensors.lidar.min_measurements_per_scan),
        )

    if sensors.imu.enabled:
        enabled_sensors.append("imu")
        imu_sensor_config = sensors.imu

        def create_imu() -> SH3001:
            bus = smbus_manager.get_bus(imu_sensor_config.bus)
            return SH3001(
                address=imu_sensor_config.address_int,
                bus=bus,
                config=SH3001Config(
                    accelerometer_range_g=(imu_sensor_config.accelerometer_range_g),
                    gyroscope_range_dps=imu_sensor_config.gyroscope_range_dps,
                ),
            )

        publishers["imu"] = IMUPublisherService(
            topic_bus,
            create_imu,
            frame_id=imu_sensor_config.frame_id,
            sample_frequency_hz=imu_sensor_config.sample_frequency_hz,
        )

    if sensors.encoder.enabled:
        enabled_sensors.append("encoder")
        publishers["encoder"] = UnavailableEncoderPublisher(
            "EncoderABC is configured, but no concrete robot-hat encoder driver "
            "has been installed"
        )

    return LocalizationSensorService(
        publishers,
        enabled_sensors=enabled_sensors,
    )


@lru_cache(maxsize=1)
def get_lidar_safety_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    motion_control_service: Annotated[
        Optional[MotionControlService], Depends(get_motion_control_service)
    ],
) -> Optional[LidarSafetyService]:
    """Build fail-safe front-sector limiting only from explicit calibration."""

    config = HardwareConfig.model_validate(config_manager.load_data())
    safety = config.lidar_safety
    if not safety.enabled:
        return None
    if motion_control_service is None:
        raise ValueError("LiDAR safety is enabled without motion control")
    if safety.stop_distance_m is None or safety.slow_distance_m is None:
        raise ValueError("LiDAR safety is enabled without measured distances")
    max_forward_speed_mps = config.motion_control.max_forward_speed_mps
    if max_forward_speed_mps is None:
        raise ValueError("LiDAR safety is enabled without forward speed calibration")
    lidar = config.localization_sensors.lidar
    return LidarSafetyService(
        topic_bus,
        motion_control_service,
        LidarSafetyEvaluator(
            LidarSafetyZone(
                front_half_angle_rad=math.radians(safety.front_half_angle_deg),
                stop_distance_m=safety.stop_distance_m,
                slow_distance_m=safety.slow_distance_m,
                max_forward_speed_mps=max_forward_speed_mps,
                sensor_x_m=lidar.transform.x_m,
                sensor_y_m=lidar.transform.y_m,
                sensor_yaw_rad=lidar.transform.yaw_rad,
                min_obstacle_points=safety.min_obstacle_points,
            )
        ),
        scan_timeout_seconds=safety.scan_timeout_ms / 1000,
    )


@lru_cache(maxsize=1)
def get_local_mapping_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> Optional[LocalMappingService]:
    """Build the opt-in local map only when its sensor prerequisites validate."""

    config = HardwareConfig.model_validate(config_manager.load_data())
    mapping = config.local_mapping
    if not mapping.enabled:
        return None
    lidar_transform = config.localization_sensors.lidar.transform
    return LocalMappingService(
        topic_bus,
        LocalOccupancyGrid(
            LocalOccupancyGridConfig(
                width_m=mapping.width_m,
                height_m=mapping.height_m,
                resolution_m=mapping.resolution_m,
                sensor_transform=StaticTransform2D(
                    x_m=lidar_transform.x_m,
                    y_m=lidar_transform.y_m,
                    yaw_rad=lidar_transform.yaw_rad,
                ),
            )
        ),
        max_odometry_age_seconds=mapping.max_odometry_age_ms / 1000,
    )


@lru_cache(maxsize=1)
def get_robot_settings_service(
    picarx_adapter: Annotated[PicarxAdapter, Depends(get_picarx_adapter)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
) -> SettingsService:
    return SettingsService(picarx=picarx_adapter, config_manager=config_manager)


@lru_cache(maxsize=1)
def get_calibration_service(
    px: Annotated[PicarxAdapter, Depends(get_picarx_adapter)],
    settings_service: Annotated[SettingsService, Depends(get_robot_settings_service)],
) -> CalibrationService:
    return CalibrationService(picarx=px, settings_service=settings_service)


@lru_cache(maxsize=1)
def get_robot_service(
    connection_manager: Annotated[ConnectionService, Depends(get_connection_manager)],
    picarx_adapter: Annotated[PicarxAdapter, Depends(get_picarx_adapter)],
    calibration_service: Annotated[
        CalibrationService, Depends(get_calibration_service)
    ],
    distance_service: Annotated[DistanceService, Depends(get_distance_service)],
    app_settings_manager: Annotated[JsonDataManager, Depends(get_app_settings_manager)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    led_service: Annotated[LEDService, Depends(get_led_service)],
    speed_estimator: Annotated[SpeedEstimator, Depends(get_speed_estimator)],
    motion_control_service: Annotated[
        Optional[MotionControlService], Depends(get_motion_control_service)
    ],
) -> CarService:
    return CarService(
        connection_manager=connection_manager,
        px=picarx_adapter,
        calibration_service=calibration_service,
        distance_service=distance_service,
        app_settings_manager=app_settings_manager,
        config_manager=config_manager,
        led_service=led_service,
        speed_estimator=speed_estimator,
        motion_control_service=motion_control_service,
    )


def get_pinout_service() -> PinoutService:
    return PinoutService()


class LifespanAppDeps(TypedDict):
    connection_service: ConnectionService
    robot_service: CarService
    settings_service: JsonDataManager
    distance_service: DistanceService
    led_service: LEDService
    speed_estimator: SpeedEstimator
    config_manager: JsonDataManager
    smbus_manager: SMBusManager
    motion_control_service: Optional[MotionControlService]
    topic_bus: TopicBus
    odometry_service: Optional[AckermannOdometryService]
    localization_sensor_service: LocalizationSensorService
    lidar_safety_service: Optional[LidarSafetyService]
    local_mapping_service: Optional[LocalMappingService]


async def get_lifespan_dependencies(
    connection_service: Annotated[ConnectionService, Depends(get_connection_manager)],
    robot_service: Annotated[CarService, Depends(get_robot_service)],
    settings_service: Annotated[JsonDataManager, Depends(get_app_settings_manager)],
    distance_service: Annotated[DistanceService, Depends(get_distance_service)],
    led_service: Annotated[LEDService, Depends(get_led_service)],
    speed_estimator: Annotated[SpeedEstimator, Depends(get_speed_estimator)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    smbus_manager: Annotated[SMBusManager, Depends(get_smbus_manager)],
    motion_control_service: Annotated[
        Optional[MotionControlService], Depends(get_motion_control_service)
    ],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    odometry_service: Annotated[
        Optional[AckermannOdometryService], Depends(get_odometry_service)
    ],
    localization_sensor_service: Annotated[
        LocalizationSensorService, Depends(get_localization_sensor_service)
    ],
    lidar_safety_service: Annotated[
        Optional[LidarSafetyService], Depends(get_lidar_safety_service)
    ],
    local_mapping_service: Annotated[
        Optional[LocalMappingService], Depends(get_local_mapping_service)
    ],
) -> AsyncGenerator[LifespanAppDeps, None]:
    deps: LifespanAppDeps = {
        "connection_service": connection_service,
        "robot_service": robot_service,
        "distance_service": distance_service,
        "settings_service": settings_service,
        "led_service": led_service,
        "speed_estimator": speed_estimator,
        "config_manager": config_manager,
        "smbus_manager": smbus_manager,
        "motion_control_service": motion_control_service,
        "topic_bus": topic_bus,
        "odometry_service": odometry_service,
        "localization_sensor_service": localization_sensor_service,
        "lidar_safety_service": lidar_safety_service,
        "local_mapping_service": local_mapping_service,
    }
    yield deps
