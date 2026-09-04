import time
import unittest
from unittest.mock import Mock

from app.api.control.autonomy import (
    clear_navigation_plan,
    get_navigation_execution,
    get_navigation_plan,
    get_localization_status,
    get_scan_matching_status,
    get_simulation_status,
    plan_navigation_goal,
    reset_simulation,
    start_navigation_execution,
)
from app.services.autonomy import (
    AckermannSimulationConfig,
    AckermannSimulationPlant,
    CoherentSimulationService,
    CoherentSimulationSupervisor,
    KnownWorldScanMatcherSupervisor,
    NavigationPlanningService,
    PoseEstimator,
    PoseEstimatorConfig,
    PoseEstimatorService,
    PoseEstimatorSupervisor,
    RobotMode,
    TopicBus,
    SimulationSensorImperfections,
    build_simulation_world,
)
from app.schemas.autonomy import (
    LocalizationPose2D,
    MappingSessionState,
    MessageHeader,
    NavigationExecutionRequest,
    NavigationGoalRequest,
    NavigationPlanState,
    OccupancyGrid,
)
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP
from fastapi import HTTPException


class FakeMotionControl:
    simulation_enabled = True

    def __init__(self) -> None:
        self.mode = RobotMode.MANUAL
        self.requested_modes: list[RobotMode] = []

    async def set_mode(self, mode: RobotMode) -> None:
        self.requested_modes.append(mode)
        self.mode = mode

    async def step(self) -> None:
        return None


class TestSimulationEndpoints(unittest.IsolatedAsyncioTestCase):
    def make_supervisor(self) -> CoherentSimulationSupervisor:
        bus = TopicBus()
        world = build_simulation_world("empty_room", width_m=6, height_m=4)
        return CoherentSimulationSupervisor(
            CoherentSimulationService(
                bus,
                AckermannSimulationPlant(
                    AckermannSimulationConfig(
                        wheelbase_m=0.25,
                        wheel_radius_m=0.03,
                        encoder_ticks_per_revolution=4096,
                    )
                ),
                world=world,
                initial_x_m=1,
                initial_y_m=-0.5,
                initial_yaw_rad=0.25,
                sensor_imperfections=SimulationSensorImperfections(
                    enabled=True,
                    random_seed=99,
                ),
            )
        )

    async def test_disabled_status_is_explicit(self) -> None:
        status = await get_simulation_status(
            CoherentSimulationSupervisor(),
            None,
        )

        self.assertFalse(status.enabled)
        self.assertFalse(status.running)
        self.assertFalse(status.physical_drive_isolated)

    async def test_reset_requires_enabled_isolated_runtime(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await reset_simulation(
                CoherentSimulationSupervisor(),
                None,
                None,
                None,
                PoseEstimatorSupervisor(),
                KnownWorldScanMatcherSupervisor(),
            )

        self.assertEqual(context.exception.status_code, 409)

    async def test_reset_disarms_and_restarts_from_initial_pose(self) -> None:
        supervisor = self.make_supervisor()
        motion = FakeMotionControl()
        odometry = Mock()
        mapping = Mock()
        pose_estimator = PoseEstimatorSupervisor()
        await supervisor.start()
        try:
            status = await reset_simulation(
                supervisor,
                motion,  # type: ignore[arg-type]
                odometry,
                mapping,
                pose_estimator,
                KnownWorldScanMatcherSupervisor(),
            )
        finally:
            await supervisor.stop()

        self.assertEqual(motion.requested_modes, [RobotMode.DISARMED])
        self.assertTrue(status.enabled)
        self.assertTrue(status.running)
        self.assertTrue(status.physical_drive_isolated)
        self.assertEqual(status.published_updates, 0)
        self.assertEqual(status.lidar_published_updates, 0)
        self.assertEqual(status.world.scenario, "empty_room")  # type: ignore[union-attr]
        self.assertEqual(status.odom_origin_in_world.x_m, 1)  # type: ignore[union-attr]
        self.assertTrue(status.sensor_imperfections.enabled)  # type: ignore[union-attr]
        self.assertEqual(status.sensor_imperfections.random_seed, 99)  # type: ignore[union-attr]
        odometry.reset.assert_called_once_with()
        mapping.reset_session.assert_called_once_with()

    async def test_localization_status_is_explicit_when_disabled(self) -> None:
        status = await get_localization_status(PoseEstimatorSupervisor())

        self.assertFalse(status.enabled)
        self.assertFalse(status.running)
        self.assertEqual(status.published_updates, 0)

    async def test_localization_status_reports_service_counters(self) -> None:
        service = PoseEstimatorService(
            TopicBus(),
            PoseEstimator(PoseEstimatorConfig()),
        )
        service.published_updates = 7
        service.imu_updates_used = 5
        supervisor = PoseEstimatorSupervisor(service)

        status = await get_localization_status(supervisor)

        self.assertTrue(status.enabled)
        self.assertEqual(status.published_updates, 7)
        self.assertEqual(status.imu_updates_used, 5)

    async def test_scan_matching_status_is_explicit_when_disabled(self) -> None:
        status = await get_scan_matching_status(KnownWorldScanMatcherSupervisor())

        self.assertFalse(status.enabled)
        self.assertFalse(status.running)
        self.assertEqual(status.matches_published, 0)

    async def test_navigation_endpoints_only_plan_and_clear_a_preview(self) -> None:
        bus = TopicBus()
        message_header = MessageHeader(
            sequence=1,
            frame_id="odom",
            timestamp_monotonic_ns=time.monotonic_ns(),
        )
        bus.publish(
            LOCAL_MAP,
            OccupancyGrid(
                header=message_header,
                width=5,
                height=5,
                resolution_m=1,
                origin_x_m=0,
                origin_y_m=0,
                data=tuple([0] * 25),
            ),
        )
        bus.publish(
            LOCALIZATION_POSE,
            LocalizationPose2D(
                header=message_header,
                x_m=0.5,
                y_m=0.5,
                yaw_rad=0,
                linear_speed_mps=0,
                yaw_rate_radps=0,
                position_variance_m2=0.001,
                yaw_variance_rad2=0.001,
                fusion_mode="corrected",
            ),
        )
        service = NavigationPlanningService(bus)

        initial = await get_navigation_plan(service)
        planned = await plan_navigation_goal(
            NavigationGoalRequest(x_m=4.5, y_m=4.5, clearance_m=0),
            service,
            None,
        )
        cleared = await clear_navigation_plan(service)

        self.assertEqual(initial.state, NavigationPlanState.IDLE)
        self.assertEqual(planned.state, NavigationPlanState.READY)
        self.assertGreater(planned.path_length_m, 0)
        self.assertEqual(cleared.state, NavigationPlanState.IDLE)

    async def test_navigation_rejects_an_active_mapping_session(self) -> None:
        mapping = Mock()
        mapping.status.state = MappingSessionState.ACTIVE

        with self.assertRaises(HTTPException) as planning_error:
            await plan_navigation_goal(
                NavigationGoalRequest(x_m=1, y_m=1),
                NavigationPlanningService(TopicBus()),
                mapping,
            )
        with self.assertRaises(HTTPException) as execution_error:
            await start_navigation_execution(
                NavigationExecutionRequest(),
                None,
                mapping,
            )

        self.assertEqual(planning_error.exception.status_code, 409)
        self.assertIn("finish mapping", planning_error.exception.detail)
        self.assertEqual(execution_error.exception.status_code, 409)
        self.assertIn("finish mapping", execution_error.exception.detail)

    async def test_navigation_execution_reports_unavailable_prerequisites(self) -> None:
        status = await get_navigation_execution(None)

        self.assertFalse(status.available)
        self.assertIn("localization", status.reason or "")


if __name__ == "__main__":
    unittest.main()
