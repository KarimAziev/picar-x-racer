import math
import unittest

from app.schemas.autonomy import (
    LocalizationPose2D,
    MessageHeader,
    NavigationGoalRequest,
    NavigationPoint,
    NavigationPlanState,
    OccupancyGrid,
)
from app.services.autonomy import (
    AckermannPathSmoother,
    NavigationPlanRejected,
    NavigationPlanningService,
    OccupancyGridPlanner,
    TopicBus,
)
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP


def header(*, sequence: int = 1, frame_id: str = "odom") -> MessageHeader:
    return MessageHeader(
        sequence=sequence,
        frame_id=frame_id,
        timestamp_monotonic_ns=sequence * 1_000_000,
    )


def grid(
    width: int,
    height: int,
    *,
    data: list[int] | None = None,
    resolution_m: float = 1.0,
    origin_x_m: float = 0.0,
    origin_y_m: float = 0.0,
    origin_yaw_rad: float = 0.0,
) -> OccupancyGrid:
    return OccupancyGrid(
        header=header(sequence=7),
        width=width,
        height=height,
        resolution_m=resolution_m,
        origin_x_m=origin_x_m,
        origin_y_m=origin_y_m,
        origin_yaw_rad=origin_yaw_rad,
        data=tuple(data if data is not None else [0] * width * height),
    )


class OccupancyGridPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = OccupancyGridPlanner()

    def test_plans_and_simplifies_a_clear_route(self) -> None:
        result = self.planner.plan(
            grid(10, 6),
            start_x_m=1.25,
            start_y_m=2.25,
            goal=NavigationGoalRequest(
                x_m=8.25,
                y_m=2.25,
                clearance_m=0,
            ),
        )

        self.assertEqual(len(result.path), 2)
        self.assertEqual(result.path[0].x_m, 1.25)
        self.assertEqual(result.path[-1].x_m, 8.25)
        self.assertAlmostEqual(result.path_length_m, 7.0)
        self.assertGreater(result.expanded_nodes, 0)

    def test_routes_through_a_wall_opening(self) -> None:
        values = [0] * (9 * 7)
        for y in range(7):
            if y != 1:
                values[y * 9 + 4] = 100

        result = self.planner.plan(
            grid(9, 7, data=values),
            start_x_m=1.5,
            start_y_m=3.5,
            goal=NavigationGoalRequest(
                x_m=7.5,
                y_m=3.5,
                clearance_m=0,
            ),
        )

        self.assertGreater(len(result.path), 2)
        self.assertTrue(any(point.y_m <= 1.5 for point in result.path))
        self.assertGreater(result.path_length_m, 6.0)

    def test_rejects_unknown_and_occupied_goals(self) -> None:
        values = [0] * 25
        values[3 * 5 + 3] = -1
        values[1 * 5 + 3] = 100
        occupancy_grid = grid(5, 5, data=values)

        with self.assertRaisesRegex(NavigationPlanRejected, "unknown"):
            self.planner.plan(
                occupancy_grid,
                start_x_m=0.5,
                start_y_m=0.5,
                goal=NavigationGoalRequest(
                    x_m=3.5,
                    y_m=3.5,
                    clearance_m=0,
                ),
            )
        with self.assertRaisesRegex(NavigationPlanRejected, "occupied"):
            self.planner.plan(
                occupancy_grid,
                start_x_m=0.5,
                start_y_m=0.5,
                goal=NavigationGoalRequest(
                    x_m=3.5,
                    y_m=1.5,
                    clearance_m=0,
                ),
            )

    def test_inflation_rejects_a_goal_too_close_to_an_obstacle(self) -> None:
        values = [0] * 49
        values[3 * 7 + 4] = 100

        with self.assertRaisesRegex(NavigationPlanRejected, "clearance"):
            self.planner.plan(
                grid(7, 7, data=values),
                start_x_m=0.5,
                start_y_m=0.5,
                goal=NavigationGoalRequest(
                    x_m=3.5,
                    y_m=3.5,
                    clearance_m=1.0,
                ),
            )

    def test_inflation_rejects_a_goal_too_close_to_map_boundary(self) -> None:
        with self.assertRaisesRegex(NavigationPlanRejected, "clearance"):
            self.planner.plan(
                grid(10, 10, resolution_m=0.1),
                start_x_m=0.5,
                start_y_m=0.5,
                goal=NavigationGoalRequest(
                    x_m=0.05,
                    y_m=0.5,
                    clearance_m=0.2,
                ),
            )

    def test_does_not_cut_diagonally_between_obstacles(self) -> None:
        values = [0] * 9
        values[1] = 100
        values[3] = 100

        with self.assertRaisesRegex(NavigationPlanRejected, "no collision-free"):
            self.planner.plan(
                grid(3, 3, data=values),
                start_x_m=0.5,
                start_y_m=0.5,
                goal=NavigationGoalRequest(
                    x_m=1.5,
                    y_m=1.5,
                    clearance_m=0,
                ),
            )

    def test_supports_a_rotated_occupancy_grid_origin(self) -> None:
        result = self.planner.plan(
            grid(
                5,
                5,
                origin_x_m=10,
                origin_y_m=20,
                origin_yaw_rad=math.pi / 2,
            ),
            start_x_m=9.5,
            start_y_m=20.5,
            goal=NavigationGoalRequest(
                x_m=9.5,
                y_m=24.5,
                clearance_m=0,
            ),
        )

        self.assertEqual(len(result.path), 2)
        self.assertAlmostEqual(result.path_length_m, 4.0)

    def test_rejects_maps_above_the_interactive_planning_limit(self) -> None:
        planner = OccupancyGridPlanner(max_cells=99)

        with self.assertRaisesRegex(NavigationPlanRejected, "too large"):
            planner.plan(
                grid(10, 10),
                start_x_m=0.5,
                start_y_m=0.5,
                goal=NavigationGoalRequest(
                    x_m=8.5,
                    y_m=8.5,
                    clearance_m=0,
                ),
            )

    def test_smooths_and_validates_with_configured_ackermann_geometry(self) -> None:
        planner = OccupancyGridPlanner(
            path_smoother=AckermannPathSmoother(
                wheelbase_m=0.18,
                max_abs_steering_angle_rad=math.radians(30),
            )
        )

        result = planner.plan(
            grid(30, 30, resolution_m=0.1),
            start_x_m=0.5,
            start_y_m=0.5,
            start_yaw_rad=0,
            goal=NavigationGoalRequest(
                x_m=2.5,
                y_m=2.5,
                clearance_m=0,
            ),
        )

        self.assertTrue(result.geometry_validated)
        self.assertTrue(result.smoothed)
        self.assertGreater(len(result.path), result.raw_waypoint_count)
        self.assertLessEqual(
            result.max_curvature_per_m or math.inf,
            (result.curvature_limit_per_m or 0) * 1.05,
        )

    def test_recovers_when_grid_route_cannot_be_smoothed_around_obstacle(self) -> None:
        values = [0] * (40 * 30)
        for cell_y in range(8, 13):
            for cell_x in range(18, 23):
                values[cell_y * 40 + cell_x] = 100
        planner = OccupancyGridPlanner(
            path_smoother=AckermannPathSmoother(
                wheelbase_m=0.18,
                max_abs_steering_angle_rad=math.radians(30),
            )
        )

        result = planner.plan(
            grid(40, 30, data=values, resolution_m=0.1),
            start_x_m=0.5,
            start_y_m=1.0,
            start_yaw_rad=0,
            goal=NavigationGoalRequest(
                x_m=2.5,
                y_m=1.0,
                clearance_m=0.1,
            ),
        )

        self.assertEqual(result.planning_method, "hybrid_astar")
        self.assertTrue(result.geometry_validated)
        self.assertGreater(result.path_length_m, 2.0)
        self.assertGreater(result.expanded_nodes, 0)
        self.assertEqual(result.path[-1], NavigationPoint(x_m=2.5, y_m=1.0))


class NavigationPlanningServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_fused_pose_and_retains_then_clears_preview(self) -> None:
        bus = TopicBus()
        bus.publish(LOCAL_MAP, grid(8, 5))
        bus.publish(
            LOCALIZATION_POSE,
            LocalizationPose2D(
                header=header(sequence=8),
                x_m=1.5,
                y_m=2.5,
                yaw_rad=0,
                linear_speed_mps=0,
                yaw_rate_radps=0,
                position_variance_m2=0.001,
                yaw_variance_rad2=0.001,
                fusion_mode="corrected",
            ),
        )
        service = NavigationPlanningService(bus)

        status = await service.plan(
            NavigationGoalRequest(x_m=6.5, y_m=2.5, clearance_m=0)
        )

        self.assertEqual(status.state, NavigationPlanState.READY)
        self.assertEqual(status.pose_source, "localization")
        self.assertEqual(status.map_sequence, 7)
        self.assertEqual(status.path[-1].x_m, 6.5)
        self.assertEqual(service.status, status)

        cleared = await service.clear()
        self.assertEqual(cleared.state, NavigationPlanState.IDLE)
        self.assertEqual(cleared.path, ())

    async def test_reports_missing_map_without_throwing(self) -> None:
        status = await NavigationPlanningService(TopicBus()).plan(
            NavigationGoalRequest(x_m=1, y_m=1)
        )

        self.assertFalse(status.available)
        self.assertEqual(status.state, NavigationPlanState.REJECTED)
        self.assertIn("no occupancy map", status.reason or "")


if __name__ == "__main__":
    unittest.main()
