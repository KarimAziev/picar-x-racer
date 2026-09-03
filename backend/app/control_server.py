"""
The application provides robot-controlling functionality, including:

- WebSockets for controlling and calibration of the robot
- Ultrasonic distance measurement
- Battery monitoring

"""

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator, Optional, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.control import api_router, tags_metadata
from app.core.px_logger import Logger
from app.services.sensors.battery_service import BatteryService

if TYPE_CHECKING:
    from robot_hat.i2c.smbus_manager import SMBusManager

    from app.managers.file_management.json_data_manager import JsonDataManager
    from app.services.connection_service import ConnectionService
    from app.services.autonomy.motion_control_service import MotionControlService
    from app.services.autonomy.steering_feedback import SteeringFeedbackService
    from app.services.autonomy.odometry import AckermannOdometryService
    from app.services.autonomy.pose_estimation import PoseEstimatorSupervisor
    from app.services.autonomy.scan_matching import KnownWorldScanMatcherSupervisor
    from app.services.autonomy.topic_bus import TopicBus
    from app.services.autonomy.sensor_publishers import LocalizationSensorService
    from app.services.autonomy.lidar_safety import LidarSafetyService
    from app.services.autonomy.local_mapping import LocalMappingService
    from app.services.autonomy.relative_motion import RelativeMotionService
    from app.services.autonomy.simulation import CoherentSimulationSupervisor
    from app.services.control.car_service import CarService
    from app.services.sensors.distance_service import DistanceService
    from app.services.sensors.led_service import LEDService
    from app.services.sensors.speed_estimator import SpeedEstimator

Logger.setup_from_env()


logger = Logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    connection_service: Optional["ConnectionService"] = None
    robot_service: Optional["CarService"] = None
    distance_service: Optional["DistanceService"] = None
    settings_service: Optional["JsonDataManager"] = None
    led_service: Optional["LEDService"] = None
    speed_estimator: Optional["SpeedEstimator"] = None
    config_manager: Optional["JsonDataManager"] = None
    smbus_manager: Optional["SMBusManager"] = None
    battery_service: Optional["BatteryService"] = None
    motion_control_service: Optional["MotionControlService"] = None
    steering_feedback_service: Optional["SteeringFeedbackService"] = None
    topic_bus: Optional["TopicBus"] = None
    odometry_service: Optional["AckermannOdometryService"] = None
    localization_sensor_service: Optional["LocalizationSensorService"] = None
    lidar_safety_service: Optional["LidarSafetyService"] = None
    local_mapping_service: Optional["LocalMappingService"] = None
    relative_motion_service: Optional["RelativeMotionService"] = None
    coherent_simulation_supervisor: Optional["CoherentSimulationSupervisor"] = None
    pose_estimator_supervisor: Optional["PoseEstimatorSupervisor"] = None
    known_world_scan_matcher_supervisor: Optional["KnownWorldScanMatcherSupervisor"] = (
        None
    )
    try:

        from app.api import robot_deps
        from app.util.solve_lifespan import solve_lifespan

        lifespan_deps = solve_lifespan(robot_deps.get_lifespan_dependencies)
        async with lifespan_deps(app) as deps:
            connection_service = deps.get("connection_service")
            robot_service = deps.get("robot_service")
            settings_service = deps.get("settings_service")
            distance_service = deps.get("distance_service")
            led_service = deps.get("led_service")
            speed_estimator = deps.get("speed_estimator")
            config_manager = deps.get("config_manager")
            smbus_manager = deps.get("smbus_manager")
            motion_control_service = deps.get("motion_control_service")
            steering_feedback_service = deps.get("steering_feedback_service")
            topic_bus = deps.get("topic_bus")
            odometry_service = deps.get("odometry_service")
            localization_sensor_service = deps.get("localization_sensor_service")
            lidar_safety_service = deps.get("lidar_safety_service")
            local_mapping_service = deps.get("local_mapping_service")
            relative_motion_service = deps.get("relative_motion_service")
            coherent_simulation_supervisor = deps.get("coherent_simulation_supervisor")
            pose_estimator_supervisor = deps.get("pose_estimator_supervisor")
            known_world_scan_matcher_supervisor = deps.get(
                "known_world_scan_matcher_supervisor"
            )

        app_loop = asyncio.get_running_loop()

        battery_service = BatteryService(
            connection_manager=connection_service,
            config_manager=config_manager,
            smbus_manager=smbus_manager,
            app_loop=app_loop,
        )

        app.state.battery_service = battery_service

        if steering_feedback_service and not (
            coherent_simulation_supervisor and coherent_simulation_supervisor.enabled
        ):
            await steering_feedback_service.start()
        if robot_service and motion_control_service:
            await robot_service.start_motion_control()
        if pose_estimator_supervisor:
            await pose_estimator_supervisor.start()
        if odometry_service:
            odometry_service.start()
        if known_world_scan_matcher_supervisor:
            await known_world_scan_matcher_supervisor.start()
        if lidar_safety_service:
            lidar_safety_service.start()
        if local_mapping_service:
            local_mapping_service.start()
        if localization_sensor_service:
            await localization_sensor_service.start()
        # Start the producer last so every bounded consumer sees the first
        # coherent encoder, IMU, LiDAR, and truth samples.
        if coherent_simulation_supervisor:
            await coherent_simulation_supervisor.start()
        app.state.localization_sensor_service = localization_sensor_service
        app.state.robot_topic_bus = topic_bus
        app.state.robot_smbus_manager = smbus_manager
        app.state.motion_control_service = motion_control_service
        app.state.steering_feedback_service = steering_feedback_service
        app.state.odometry_service = odometry_service
        app.state.lidar_safety_service = lidar_safety_service
        app.state.local_mapping_service = local_mapping_service
        app.state.relative_motion_service = relative_motion_service
        app.state.coherent_simulation_supervisor = coherent_simulation_supervisor
        app.state.pose_estimator_supervisor = pose_estimator_supervisor
        app.state.known_world_scan_matcher_supervisor = (
            known_world_scan_matcher_supervisor
        )

        async def broadcast_distance(distance: float) -> None:
            rel_speed = (
                cast(int, robot_service.current_state["speed"]) if robot_service else 0
            )
            speed = (
                speed_estimator.process_distance(
                    distance,
                    distance_service.interval,
                    relative_speed=rel_speed,
                )
                if speed_estimator
                else None
            )
            await connection_service.broadcast_json(
                {"type": "distance", "payload": {"distance": distance, "speed": speed}}
            )

        battery_service.setup_connection_manager()
        distance_service.subscribe(broadcast_distance)

        settings = settings_service.load_data()
        robot_settings = settings.get("robot", {})

        distance_interval = robot_settings.get("auto_measure_distance_delay_ms", 1000)
        distance_secs = distance_interval / 1000

        distance_service.interval = distance_secs

        auto_measure_distance_mode = robot_settings.get(
            "auto_measure_distance_mode", False
        )

        if auto_measure_distance_mode:
            await distance_service.start_all()

        port = app.state.port if hasattr(app.state, "port") else 8001
        logger.info(f"Starting {app.title} app on the port {port}")

        yield
    except asyncio.CancelledError:
        logger.warning(
            "Lifespan was cancelled mid-shutdown (first-level). Proceeding to final cleanup."
        )

    if battery_service:
        try:
            await battery_service.cleanup_connection_manager()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up battery_service.")
            raise

    if relative_motion_service:
        try:
            await relative_motion_service.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up relative motion.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup relative motion service: %s", e)

    if robot_service:
        try:
            await robot_service.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up robot_service.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup robot service: %s", e)

    if coherent_simulation_supervisor:
        try:
            await coherent_simulation_supervisor.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up coherent simulation.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup coherent simulation: %s", e)

    if known_world_scan_matcher_supervisor:
        try:
            await known_world_scan_matcher_supervisor.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up known-world scan matcher.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup known-world scan matcher: %s", e)

    if pose_estimator_supervisor:
        try:
            await pose_estimator_supervisor.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up pose estimator.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup pose estimator: %s", e)

    if distance_service:
        try:
            await distance_service.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up distance service.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup distance service: %s", e)

    if led_service:
        try:
            await led_service.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up LED service.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup LED service: %s", e)

    if odometry_service:
        try:
            await odometry_service.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up odometry service.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup odometry service: %s", e)

    if steering_feedback_service:
        try:
            await steering_feedback_service.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up steering feedback.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup steering feedback service: %s", e)

    if localization_sensor_service:
        try:
            await localization_sensor_service.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up localization sensors.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup localization sensors: %s", e)

    if local_mapping_service:
        try:
            await local_mapping_service.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up local mapping.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup local mapping service: %s", e)

    if lidar_safety_service:
        try:
            await lidar_safety_service.stop()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up LiDAR safety.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup LiDAR safety service: %s", e)

    if topic_bus:
        topic_bus.close()

    logger.info(f"Stopped {app.title}")


app = FastAPI(
    title="Robot Control Application",
    version="1.0.0",
    summary="API for the robot's hardware interactions.",
    description=__doc__ or "",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "Karim Aziiev",
        "email": "karim.aziiev@gmail.com",
    },
    license_info={
        "name": "GNU General Public License v3.0 or later",
        "identifier": "GPL-3.0-or-later",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
