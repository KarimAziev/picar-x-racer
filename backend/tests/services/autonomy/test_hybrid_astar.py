import math
import unittest
from typing import Sequence

from app.schemas.autonomy import NavigationPoint
from app.services.autonomy import (
    HybridAStarPlanner,
    HybridPathNotFound,
    HybridPose,
)


class HybridAStarPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = HybridAStarPlanner(
            curvature_limit_per_m=3.2,
            max_expanded_nodes=10_000,
        )

    def test_searches_position_and_heading_around_an_obstacle(self) -> None:
        def avoids_obstacle(path: Sequence[NavigationPoint]) -> bool:
            return all(
                -1.5 < point.x_m < 3.5
                and -2 < point.y_m < 2
                and math.hypot(point.x_m - 1.0, point.y_m) > 0.32
                for point in path
            )

        result = self.planner.plan(
            start=HybridPose(x_m=0, y_m=0, yaw_rad=0),
            goal=NavigationPoint(x_m=2, y_m=0),
            grid_resolution_m=0.05,
            is_clear=avoids_obstacle,
            guide_path=(
                NavigationPoint(x_m=0, y_m=0),
                NavigationPoint(x_m=2, y_m=0),
            ),
        )

        self.assertEqual(result.path[0], NavigationPoint(x_m=0, y_m=0))
        self.assertEqual(result.path[-1], NavigationPoint(x_m=2, y_m=0))
        self.assertGreater(result.expanded_nodes, 1)
        self.assertTrue(avoids_obstacle(result.path))
        self.assertTrue(any(abs(point.y_m) > 0.32 for point in result.path))

    def test_can_reach_a_goal_behind_with_forward_only_turns(self) -> None:
        result = self.planner.plan(
            start=HybridPose(x_m=0, y_m=0, yaw_rad=0),
            goal=NavigationPoint(x_m=-1, y_m=0),
            grid_resolution_m=0.05,
            is_clear=lambda path: all(
                -2 < point.x_m < 2 and -2 < point.y_m < 2 for point in path
            ),
        )

        self.assertEqual(result.path[-1], NavigationPoint(x_m=-1, y_m=0))
        self.assertTrue(any(abs(point.y_m) > 0.25 for point in result.path))

    def test_honors_the_interactive_expansion_bound(self) -> None:
        planner = HybridAStarPlanner(
            curvature_limit_per_m=3.2,
            max_expanded_nodes=30,
        )

        with self.assertRaisesRegex(HybridPathNotFound, "expansion limit"):
            planner.plan(
                start=HybridPose(x_m=0, y_m=0, yaw_rad=0),
                goal=NavigationPoint(x_m=3, y_m=0),
                grid_resolution_m=0.05,
                is_clear=lambda path: all(point.x_m < 0.4 for point in path),
            )


if __name__ == "__main__":
    unittest.main()
