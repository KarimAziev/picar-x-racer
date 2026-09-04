import math
from functools import lru_cache
from typing import (
    Annotated,
    AsyncGenerator,
    Callable,
    Dict,
    Literal,
    Optional,
    TypedDict,
)

from app.adapters.picarx_adapter import PicarxAdapter
from app.config.config import settings as app_config
from app.core.async_emitter import AsyncEventEmitter
from app.core.logger import Logger
from app.managers.async_task_manager import AsyncTaskManager
from app.managers.file_management.json_data_manager import JsonDataManager
from app.migrations.robot_config import create_robot_config_migrator
from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.localization_sensors import (
    AS5048AEncoderConfig,
    AS5048ASteeringPositionConfig,
    AS5600LEncoderConfig,
    AS5600LSteeringPositionConfig,
    GPIOQuadratureEncoderConfig,
    MockEncoderConfig,
    MockIMUSensorConfig,
    MockLidarSensorConfig,
    MockSteeringPositionConfig,
)
from app.schemas.autonomy import SensorName
from app.services.connection_service import ConnectionService
from app.services.autonomy import (
    AckermannPathSmoother,
    AckermannOdometryConfig,
    AckermannOdometryEstimator,
    AckermannOdometryService,
    ActuationCalibration,
    AckermannSimulationConfig,
    AckermannSimulationPlant,
    CoherentSimulationService,
    CoherentSimulationSupervisor,
    SimulationSensorImperfections,
    EncoderPublisherService,
    HardwareController,
    LinearActuatorTranslator,
    LaserScanConverter,
    RaycastLidarConfig,
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
    NavigationExecutionService,
    NavigationPlanningService,
    OccupancyGridPlanner,
    KnownWorldScanMatcher,
    KnownWorldScanMatcherConfig,
    KnownWorldScanMatcherService,
    KnownWorldScanMatcherSupervisor,
    PoseEstimator,
    PoseEstimatorConfig,
    PoseEstimatorService,
    PoseEstimatorSupervisor,
    TopicBus,
    TopicSensorMonitor,
    StaticTransform2D,
    RelativeMotionService,
    SelectableDriveHardware,
    SteeringAngleCalibration,
    SteeringCalibrationPoint,
    SteeringFeedbackService,
    VirtualDriveHardware,
    WorldLidarRaycaster,
    build_simulation_world,
)
from app.services.autonomy.sensor_publishers import SensorPublisher
from app.services.autonomy.topics import ENCODER_STATE, IMU_DATA, LIDAR_SCAN
from app.services.control.calibration_service import CalibrationService
from app.services.control.car_service import CarService
from app.services.control.settings_service import SettingsService
from app.services.sensors.distance_service import DistanceService
from app.services.sensors.led_service import LEDService
from app.services.sensors.pinout_service import PinoutService
from app.services.sensors.speed_estimator import SpeedEstimator
from fastapi import Depends
from robot_hat.i2c.smbus_manager import SMBusManager
from robot_hat import (
    AS5048AAngularPosition,
    AS5048AEncoder,
    AS5600LAngularPosition,
    AS5600LEncoder,
    AngularPositionABC,
    EncoderABC,
    IMUABC,
    Lidar2DABC,
    MockEncoder,
    MockAngularPosition,
    MockIMU,
    MockLidar2D,
    GPIOQuadratureCounterBackend,
    GPIOZeroDigitalEdgeInput,
    QuadratureDecodeMode,
    QuadratureEncoder,
    RPLidarC1,
    RPLidarC1Config,
    SH3001,
    SH3001Config,
)

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
def get_selectable_drive_hardware(
    picarx_adapter: Annotated[PicarxAdapter, Depends(get_picarx_adapter)],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
) -> SelectableDriveHardware:
    config = HardwareConfig.model_validate(config_manager.load_data())
    return SelectableDriveHardware(
        picarx_adapter,
        VirtualDriveHardware(),
        simulation_enabled=config.coherent_simulation.enabled,
    )


def build_steering_feedback_service(
    config: HardwareConfig,
    smbus_manager: SMBusManager,
) -> Optional[SteeringFeedbackService]:
    """Build optional steering feedback without opening its hardware yet."""

    steering = config.localization_sensors.steering
    if not steering.enabled:
        return None

    sensor_factory: Callable[[], AngularPositionABC]
    if isinstance(steering, AS5048ASteeringPositionConfig):
        sensor_factory = lambda: AS5048AAngularPosition(
            bus=steering.bus,
            device=steering.device,
            max_speed_hz=steering.max_speed_hz,
        )
    elif isinstance(steering, AS5600LSteeringPositionConfig):
        sensor_factory = lambda: AS5600LAngularPosition(
            bus=smbus_manager.get_bus(steering.bus),
            address=steering.address_int,
        )
    elif isinstance(steering, MockSteeringPositionConfig):
        sensor_factory = lambda: MockAngularPosition(
            initial_angle_degrees=steering.initial_angle_degrees,
            degrees_per_sample=steering.degrees_per_sample,
        )
    else:
        raise TypeError(f"unsupported steering position config: {type(steering)!r}")

    return SteeringFeedbackService(
        sensor_factory,
        SteeringAngleCalibration(
            center_angle_deg=steering.center_angle_deg,
            invert_direction=steering.invert_direction,
            wheel_degrees_per_sensor_degree=(steering.wheel_degrees_per_sensor_degree),
            points=tuple(
                SteeringCalibrationPoint(
                    sensor_offset_deg=point.sensor_offset_deg,
                    wheel_angle_rad=point.wheel_angle_rad,
                )
                for point in steering.calibration_points
            ),
        ),
        sample_frequency_hz=steering.sample_frequency_hz,
    )


@lru_cache(maxsize=1)
def get_steering_feedback_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    smbus_manager: Annotated[SMBusManager, Depends(get_smbus_manager)],
) -> Optional[SteeringFeedbackService]:
    config = HardwareConfig.model_validate(config_manager.load_data())
    return build_steering_feedback_service(config, smbus_manager)


@lru_cache(maxsize=1)
def get_motion_control_service(
    drive_hardware: Annotated[
        SelectableDriveHardware, Depends(get_selectable_drive_hardware)
    ],
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    steering_feedback_service: Annotated[
        Optional[SteeringFeedbackService], Depends(get_steering_feedback_service)
    ],
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
            drive_hardware,
            LinearActuatorTranslator(calibration),
        ),
        control_period_seconds=1.0 / motion.control_frequency_hz,
        topic_bus=topic_bus,
        steering_feedback=steering_feedback_service,
        drive_hardware=drive_hardware,
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
    return AckermannOdometryService(topic_bus, build_odometry_estimator(config))


def build_odometry_estimator(config: HardwareConfig) -> AckermannOdometryEstimator:
    """Create a fresh estimator from complete, enabled odometry settings."""

    odometry = config.ackermann_odometry
    if (
        not odometry.enabled
        or odometry.wheelbase_m is None
        or odometry.wheel_radius_m is None
        or odometry.encoder_ticks_per_revolution is None
    ):
        raise ValueError("Ackermann odometry configuration is not enabled and complete")
    return AckermannOdometryEstimator(
        AckermannOdometryConfig(
            wheelbase_m=odometry.wheelbase_m,
            wheel_radius_m=odometry.wheel_radius_m,
            encoder_ticks_per_revolution=odometry.encoder_ticks_per_revolution,
            gear_ratio=odometry.gear_ratio,
            max_steering_age_seconds=odometry.max_steering_age_ms / 1000,
        )
    )


def build_pose_estimator_supervisor(
    config: HardwareConfig,
    topic_bus: TopicBus,
) -> PoseEstimatorSupervisor:
    """Build optional wheel/IMU fusion behind a stable lifecycle handle."""

    settings = config.pose_estimation
    if not settings.enabled:
        return PoseEstimatorSupervisor()
    if not config.ackermann_odometry.enabled:
        raise ValueError("pose estimation requires Ackermann odometry")
    estimator = PoseEstimator(
        PoseEstimatorConfig(
            imu_yaw_rate_weight=settings.imu_yaw_rate_weight,
            max_imu_age_seconds=settings.max_imu_age_ms / 1000,
            max_pose_observation_age_seconds=(
                settings.max_pose_observation_age_ms / 1000
            ),
            initial_position_stddev_m=settings.initial_position_stddev_m,
            initial_heading_stddev_rad=settings.initial_heading_stddev_rad,
            position_process_noise_m_per_meter=(
                settings.position_process_noise_m_per_meter
            ),
            heading_process_noise_rad_per_second=(
                settings.heading_process_noise_rad_per_second
            ),
            odometry_heading_noise_fraction=(settings.odometry_heading_noise_fraction),
            imu_yaw_rate_stddev_radps=settings.imu_yaw_rate_stddev_radps,
        )
    )
    return PoseEstimatorSupervisor(PoseEstimatorService(topic_bus, estimator))


@lru_cache(maxsize=1)
def get_pose_estimator_supervisor(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> PoseEstimatorSupervisor:
    config = HardwareConfig.model_validate(config_manager.load_data())
    return build_pose_estimator_supervisor(config, topic_bus)


def build_known_world_scan_matcher_supervisor(
    config: HardwareConfig,
    topic_bus: TopicBus,
) -> KnownWorldScanMatcherSupervisor:
    """Build the development scan matcher without exposing simulator truth."""

    settings = config.pose_estimation.simulation_scan_matching
    if not settings.enabled:
        return KnownWorldScanMatcherSupervisor()
    simulation = config.coherent_simulation
    lidar = config.localization_sensors.lidar
    world = build_simulation_world(
        simulation.world_scenario,
        width_m=simulation.world_width_m,
        height_m=simulation.world_height_m,
    )
    matcher = KnownWorldScanMatcher(
        world,
        KnownWorldScanMatcherConfig(
            odom_origin_in_world=(
                simulation.initial_x_m,
                simulation.initial_y_m,
                simulation.initial_yaw_rad,
            ),
            sensor_transform=StaticTransform2D(
                x_m=lidar.transform.x_m,
                y_m=lidar.transform.y_m,
                yaw_rad=lidar.transform.yaw_rad,
            ),
            expected_scan_frame_id=lidar.frame_id,
            search_translation_m=settings.search_translation_m,
            search_heading_rad=math.radians(settings.search_heading_deg),
            coarse_translation_step_m=settings.coarse_translation_step_m,
            coarse_heading_step_rad=math.radians(settings.coarse_heading_step_deg),
            refinement_translation_step_m=(settings.refinement_translation_step_m),
            refinement_heading_step_rad=math.radians(
                settings.refinement_heading_step_deg
            ),
            max_scan_points=settings.max_scan_points,
            min_valid_points=settings.min_valid_points,
            max_mean_error_m=settings.max_mean_error_m,
            max_residual_m=settings.max_residual_m,
            position_stddev_m=settings.position_stddev_m,
            heading_stddev_rad=math.radians(settings.heading_stddev_deg),
        ),
    )
    return KnownWorldScanMatcherSupervisor(
        KnownWorldScanMatcherService(
            topic_bus,
            matcher,
            max_pose_age_seconds=settings.max_pose_age_ms / 1000,
        )
    )


@lru_cache(maxsize=1)
def get_known_world_scan_matcher_supervisor(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> KnownWorldScanMatcherSupervisor:
    config = HardwareConfig.model_validate(config_manager.load_data())
    return build_known_world_scan_matcher_supervisor(config, topic_bus)


def build_localization_sensor_service(
    config: HardwareConfig,
    topic_bus: TopicBus,
    smbus_manager: SMBusManager,
) -> LocalizationSensorService:
    """Build lazy, opt-in hardware publishers from validated configuration."""

    sensors = config.localization_sensors
    coherent_simulation = config.coherent_simulation.enabled
    publishers: Dict[SensorName, SensorPublisher] = {}
    enabled_sensors = []

    if sensors.lidar.enabled:
        enabled_sensors.append("lidar")
        lidar_sensor_config = sensors.lidar
        if coherent_simulation:
            publishers["lidar"] = TopicSensorMonitor(
                "lidar",
                topic_bus,
                LIDAR_SCAN,
            )
        else:
            range_min_m = lidar_sensor_config.range_min_m
            range_max_m = lidar_sensor_config.range_max_m
            if range_min_m is None or range_max_m is None:
                raise ValueError("enabled lidar requires calibrated range limits")
            lidar_factory: Callable[[], Lidar2DABC]
            if isinstance(lidar_sensor_config, MockLidarSensorConfig):
                lidar_factory = lambda: MockLidar2D(
                    points_per_scan=lidar_sensor_config.points_per_scan,
                    distance_m=lidar_sensor_config.distance_m,
                    quality=lidar_sensor_config.quality,
                    scan_frequency_hz=lidar_sensor_config.scan_frequency_hz,
                )
            else:
                lidar_config = RPLidarC1Config(
                    port=lidar_sensor_config.port,
                    baudrate=lidar_sensor_config.baudrate,
                    timeout=lidar_sensor_config.timeout_s,
                )
                lidar_factory = lambda: RPLidarC1(lidar_config)

            publishers["lidar"] = LidarPublisherService(
                topic_bus,
                lidar_factory,
                LaserScanConverter(
                    frame_id=lidar_sensor_config.frame_id,
                    range_min_m=range_min_m,
                    range_max_m=range_max_m,
                    angular_resolution_deg=(lidar_sensor_config.angular_resolution_deg),
                ),
                min_measurements_per_scan=(
                    lidar_sensor_config.min_measurements_per_scan
                ),
            )

    if coherent_simulation:
        enabled_sensors.extend(("imu", "encoder"))
        publishers["imu"] = TopicSensorMonitor("imu", topic_bus, IMU_DATA)
        publishers["encoder"] = TopicSensorMonitor(
            "encoder",
            topic_bus,
            ENCODER_STATE,
        )

    if sensors.imu.enabled and not coherent_simulation:
        enabled_sensors.append("imu")
        imu_sensor_config = sensors.imu
        imu_factory: Callable[[], IMUABC]

        if isinstance(imu_sensor_config, MockIMUSensorConfig):
            imu_factory = lambda: MockIMU(
                acceleration_mps2=imu_sensor_config.acceleration_mps2,
                angular_velocity_radps=(imu_sensor_config.angular_velocity_radps),
            )
        else:
            imu_factory = lambda: SH3001(
                address=imu_sensor_config.address_int,
                bus=smbus_manager.get_bus(imu_sensor_config.bus),
                config=SH3001Config(
                    accelerometer_range_g=(imu_sensor_config.accelerometer_range_g),
                    gyroscope_range_dps=imu_sensor_config.gyroscope_range_dps,
                ),
            )

        publishers["imu"] = IMUPublisherService(
            topic_bus,
            imu_factory,
            frame_id=imu_sensor_config.frame_id,
            sample_frequency_hz=imu_sensor_config.sample_frequency_hz,
        )

    if sensors.encoder.enabled and not coherent_simulation:
        enabled_sensors.append("encoder")
        encoder_factories: Dict[Literal["left", "right"], Callable[[], EncoderABC]] = {}
        for encoder_sensor_config in sensors.encoder.sensors:
            if isinstance(encoder_sensor_config, AS5048AEncoderConfig):

                def create_as5048a_encoder(
                    sensor_config: AS5048AEncoderConfig = encoder_sensor_config,
                ) -> AS5048AEncoder:
                    return AS5048AEncoder(
                        bus=sensor_config.bus,
                        device=sensor_config.device,
                        max_speed_hz=sensor_config.max_speed_hz,
                        invert_direction=sensor_config.invert_direction,
                        max_sample_gap_ns=sensor_config.max_sample_gap_ns,
                        max_abs_speed_rps=sensor_config.max_abs_speed_rps,
                    )

                encoder_factories[encoder_sensor_config.side] = create_as5048a_encoder
            elif isinstance(encoder_sensor_config, AS5600LEncoderConfig):

                def create_as5600l_encoder(
                    sensor_config: AS5600LEncoderConfig = encoder_sensor_config,
                ) -> AS5600LEncoder:
                    return AS5600LEncoder(
                        bus=smbus_manager.get_bus(sensor_config.bus),
                        address=sensor_config.address_int,
                        invert_direction=sensor_config.invert_direction,
                        max_sample_gap_ns=sensor_config.max_sample_gap_ns,
                        max_abs_speed_rps=sensor_config.max_abs_speed_rps,
                    )

                encoder_factories[encoder_sensor_config.side] = create_as5600l_encoder
            elif isinstance(encoder_sensor_config, GPIOQuadratureEncoderConfig):

                def create_gpio_quadrature_encoder(
                    sensor_config: GPIOQuadratureEncoderConfig = (
                        encoder_sensor_config
                    ),
                ) -> QuadratureEncoder:
                    decode_mode = {
                        "x1": QuadratureDecodeMode.X1,
                        "x2": QuadratureDecodeMode.X2,
                        "x4": QuadratureDecodeMode.X4,
                    }[sensor_config.decode_mode]
                    return QuadratureEncoder(
                        backend=GPIOQuadratureCounterBackend(
                            a_input=GPIOZeroDigitalEdgeInput(
                                sensor_config.a_pin,
                                pull_up=sensor_config.pull_up,
                                active_state=sensor_config.active_state,
                            ),
                            b_input=GPIOZeroDigitalEdgeInput(
                                sensor_config.b_pin,
                                pull_up=sensor_config.pull_up,
                                active_state=sensor_config.active_state,
                            ),
                            decode_mode=decode_mode,
                        ),
                        invert_direction=sensor_config.invert_direction,
                    )

                encoder_factories[encoder_sensor_config.side] = (
                    create_gpio_quadrature_encoder
                )
            elif isinstance(encoder_sensor_config, MockEncoderConfig):

                def create_mock_encoder(
                    sensor_config: MockEncoderConfig = encoder_sensor_config,
                ) -> MockEncoder:
                    return MockEncoder(
                        initial_ticks=sensor_config.initial_ticks,
                        ticks_per_sample=(
                            -sensor_config.ticks_per_sample
                            if sensor_config.invert_direction
                            else sensor_config.ticks_per_sample
                        ),
                    )

                encoder_factories[encoder_sensor_config.side] = create_mock_encoder

        publishers["encoder"] = EncoderPublisherService(
            topic_bus,
            encoder_factories,
            frame_id=sensors.encoder.frame_id,
            sample_frequency_hz=sensors.encoder.sample_frequency_hz,
        )

    return LocalizationSensorService(
        publishers,
        enabled_sensors=enabled_sensors,
    )


def build_coherent_simulation_supervisor(
    config: HardwareConfig,
    topic_bus: TopicBus,
) -> CoherentSimulationSupervisor:
    """Build an enabled simulator or a stable disabled lifecycle handle."""

    simulation = config.coherent_simulation
    if not simulation.enabled:
        return CoherentSimulationSupervisor()
    odometry = config.ackermann_odometry
    if (
        odometry.wheelbase_m is None
        or odometry.wheel_radius_m is None
        or odometry.encoder_ticks_per_revolution is None
    ):
        raise ValueError("coherent simulation requires complete Ackermann geometry")
    world = build_simulation_world(
        simulation.world_scenario,
        width_m=simulation.world_width_m,
        height_m=simulation.world_height_m,
    )
    if world.collides_circle(
        simulation.initial_x_m,
        simulation.initial_y_m,
        simulation.vehicle_radius_m,
    ):
        raise ValueError("coherent simulation initial pose collides with the world")
    lidar = config.localization_sensors.lidar
    lidar_raycaster = None
    if lidar.enabled:
        if lidar.range_min_m is None or lidar.range_max_m is None:
            raise ValueError("coherent simulation requires calibrated LiDAR ranges")
        lidar_raycaster = WorldLidarRaycaster(
            world,
            RaycastLidarConfig(
                frame_id=lidar.frame_id,
                sensor_x_m=lidar.transform.x_m,
                sensor_y_m=lidar.transform.y_m,
                sensor_yaw_rad=lidar.transform.yaw_rad,
                range_min_m=lidar.range_min_m,
                range_max_m=lidar.range_max_m,
                angular_resolution_deg=lidar.angular_resolution_deg,
                scan_frequency_hz=simulation.lidar_scan_frequency_hz,
                quality=simulation.lidar_quality,
            ),
        )
    service = CoherentSimulationService(
        topic_bus,
        AckermannSimulationPlant(
            AckermannSimulationConfig(
                wheelbase_m=odometry.wheelbase_m,
                wheel_radius_m=odometry.wheel_radius_m,
                encoder_ticks_per_revolution=(odometry.encoder_ticks_per_revolution),
                gear_ratio=odometry.gear_ratio,
                update_frequency_hz=simulation.update_frequency_hz,
                command_timeout_seconds=simulation.command_timeout_ms / 1000,
            ),
            collision_checker=lambda x_m, y_m: world.collides_circle(
                x_m,
                y_m,
                simulation.vehicle_radius_m,
            ),
        ),
        initial_x_m=simulation.initial_x_m,
        initial_y_m=simulation.initial_y_m,
        initial_yaw_rad=simulation.initial_yaw_rad,
        world=world,
        lidar_raycaster=lidar_raycaster,
        sensor_imperfections=SimulationSensorImperfections(
            enabled=simulation.sensor_imperfections.enabled,
            random_seed=simulation.sensor_imperfections.random_seed,
            encoder_scale_error_percent=(
                simulation.sensor_imperfections.encoder_scale_error_percent
            ),
            encoder_noise_stddev_ticks=(
                simulation.sensor_imperfections.encoder_noise_stddev_ticks
            ),
            steering_bias_deg=simulation.sensor_imperfections.steering_bias_deg,
            steering_noise_stddev_deg=(
                simulation.sensor_imperfections.steering_noise_stddev_deg
            ),
            imu_yaw_rate_bias_radps=(
                simulation.sensor_imperfections.imu_yaw_rate_bias_radps
            ),
            imu_yaw_rate_noise_stddev_radps=(
                simulation.sensor_imperfections.imu_yaw_rate_noise_stddev_radps
            ),
            lidar_range_noise_stddev_m=(
                simulation.sensor_imperfections.lidar_range_noise_stddev_m
            ),
            lidar_dropout_probability=(
                simulation.sensor_imperfections.lidar_dropout_probability
            ),
        ),
    )
    return CoherentSimulationSupervisor(service)


@lru_cache(maxsize=1)
def get_coherent_simulation_supervisor(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> CoherentSimulationSupervisor:
    config = HardwareConfig.model_validate(config_manager.load_data())
    return build_coherent_simulation_supervisor(config, topic_bus)


@lru_cache(maxsize=1)
def get_localization_sensor_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    smbus_manager: Annotated[SMBusManager, Depends(get_smbus_manager)],
) -> LocalizationSensorService:
    """Build the stable supervisor used by lifespan and diagnostics endpoints."""

    config = HardwareConfig.model_validate(config_manager.load_data())
    return build_localization_sensor_service(config, topic_bus, smbus_manager)


def build_lidar_safety_service(
    config: HardwareConfig,
    topic_bus: TopicBus,
    motion_control_service: Optional[MotionControlService],
) -> Optional[LidarSafetyService]:
    """Build fail-safe front/rear limiting only from explicit calibration."""

    safety = config.lidar_safety
    if not safety.enabled:
        return None
    if motion_control_service is None:
        raise ValueError("LiDAR safety is enabled without motion control")
    if safety.stop_distance_m is None or safety.slow_distance_m is None:
        raise ValueError("LiDAR safety is enabled without measured distances")
    max_forward_speed_mps = config.motion_control.max_forward_speed_mps
    max_reverse_speed_mps = config.motion_control.max_reverse_speed_mps
    if max_forward_speed_mps is None or max_reverse_speed_mps is None:
        raise ValueError(
            "LiDAR safety is enabled without directional speed calibration"
        )
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
                max_reverse_speed_mps=max_reverse_speed_mps,
                sensor_x_m=lidar.transform.x_m,
                sensor_y_m=lidar.transform.y_m,
                sensor_yaw_rad=lidar.transform.yaw_rad,
                min_obstacle_points=safety.min_obstacle_points,
            )
        ),
        scan_timeout_seconds=safety.scan_timeout_ms / 1000,
    )


@lru_cache(maxsize=1)
def get_lidar_safety_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    motion_control_service: Annotated[
        Optional[MotionControlService], Depends(get_motion_control_service)
    ],
) -> Optional[LidarSafetyService]:
    config = HardwareConfig.model_validate(config_manager.load_data())
    return build_lidar_safety_service(config, topic_bus, motion_control_service)


def build_local_mapping_service(
    config: HardwareConfig,
    topic_bus: TopicBus,
) -> Optional[LocalMappingService]:
    """Build the opt-in local map only when its sensor prerequisites validate."""

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
        prefer_localization=config.pose_estimation.enabled,
    )


@lru_cache(maxsize=1)
def get_local_mapping_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> Optional[LocalMappingService]:
    config = HardwareConfig.model_validate(config_manager.load_data())
    return build_local_mapping_service(config, topic_bus)


@lru_cache(maxsize=1)
def get_navigation_planning_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
) -> NavigationPlanningService:
    """Return a goal planner configured with the vehicle's steering geometry."""

    config = HardwareConfig.model_validate(config_manager.load_data())
    odometry = config.ackermann_odometry
    path_smoother = None
    if odometry.enabled and odometry.wheelbase_m is not None:
        max_steering_degrees = min(
            abs(config.steering_servo.min_angle),
            abs(config.steering_servo.max_angle),
        )
        if max_steering_degrees > 0:
            path_smoother = AckermannPathSmoother(
                wheelbase_m=odometry.wheelbase_m,
                max_abs_steering_angle_rad=math.radians(max_steering_degrees),
            )
    return NavigationPlanningService(
        topic_bus,
        OccupancyGridPlanner(path_smoother=path_smoother),
    )


@lru_cache(maxsize=1)
def get_navigation_execution_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    motion_control_service: Annotated[
        Optional[MotionControlService], Depends(get_motion_control_service)
    ],
    planning_service: Annotated[
        NavigationPlanningService, Depends(get_navigation_planning_service)
    ],
) -> Optional[NavigationExecutionService]:
    config = HardwareConfig.model_validate(config_manager.load_data())
    odometry = config.ackermann_odometry
    if (
        motion_control_service is None
        or not odometry.enabled
        or not config.pose_estimation.enabled
        or odometry.wheelbase_m is None
    ):
        return None
    max_steering_degrees = min(
        abs(config.steering_servo.min_angle),
        abs(config.steering_servo.max_angle),
    )
    return NavigationExecutionService(
        topic_bus,
        motion_control_service,
        planning_service,
        wheelbase_m=odometry.wheelbase_m,
        max_abs_steering_angle_rad=math.radians(max_steering_degrees),
    )


@lru_cache(maxsize=1)
def get_relative_motion_service(
    config_manager: Annotated[JsonDataManager, Depends(get_config_manager)],
    topic_bus: Annotated[TopicBus, Depends(get_robot_topic_bus)],
    motion_control_service: Annotated[
        Optional[MotionControlService], Depends(get_motion_control_service)
    ],
) -> Optional[RelativeMotionService]:
    config = HardwareConfig.model_validate(config_manager.load_data())
    if motion_control_service is None or not config.ackermann_odometry.enabled:
        return None
    wheelbase_m = config.ackermann_odometry.wheelbase_m
    if wheelbase_m is None:
        raise ValueError("Relative motion requires a calibrated wheelbase")
    max_steering_degrees = min(
        abs(config.steering_servo.min_angle),
        abs(config.steering_servo.max_angle),
    )
    return RelativeMotionService(
        topic_bus,
        motion_control_service,
        wheelbase_m=wheelbase_m,
        max_abs_steering_angle_rad=math.radians(max_steering_degrees),
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
    steering_feedback_service: Optional[SteeringFeedbackService]
    topic_bus: TopicBus
    odometry_service: Optional[AckermannOdometryService]
    localization_sensor_service: LocalizationSensorService
    lidar_safety_service: Optional[LidarSafetyService]
    local_mapping_service: Optional[LocalMappingService]
    relative_motion_service: Optional[RelativeMotionService]
    navigation_execution_service: Optional[NavigationExecutionService]
    coherent_simulation_supervisor: CoherentSimulationSupervisor
    pose_estimator_supervisor: PoseEstimatorSupervisor
    known_world_scan_matcher_supervisor: KnownWorldScanMatcherSupervisor


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
    steering_feedback_service: Annotated[
        Optional[SteeringFeedbackService], Depends(get_steering_feedback_service)
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
    relative_motion_service: Annotated[
        Optional[RelativeMotionService], Depends(get_relative_motion_service)
    ],
    navigation_execution_service: Annotated[
        Optional[NavigationExecutionService],
        Depends(get_navigation_execution_service),
    ],
    coherent_simulation_supervisor: Annotated[
        CoherentSimulationSupervisor,
        Depends(get_coherent_simulation_supervisor),
    ],
    pose_estimator_supervisor: Annotated[
        PoseEstimatorSupervisor,
        Depends(get_pose_estimator_supervisor),
    ],
    known_world_scan_matcher_supervisor: Annotated[
        KnownWorldScanMatcherSupervisor,
        Depends(get_known_world_scan_matcher_supervisor),
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
        "steering_feedback_service": steering_feedback_service,
        "topic_bus": topic_bus,
        "odometry_service": odometry_service,
        "localization_sensor_service": localization_sensor_service,
        "lidar_safety_service": lidar_safety_service,
        "local_mapping_service": local_mapping_service,
        "relative_motion_service": relative_motion_service,
        "navigation_execution_service": navigation_execution_service,
        "coherent_simulation_supervisor": coherent_simulation_supervisor,
        "pose_estimator_supervisor": pose_estimator_supervisor,
        "known_world_scan_matcher_supervisor": (known_world_scan_matcher_supervisor),
    }
    yield deps
