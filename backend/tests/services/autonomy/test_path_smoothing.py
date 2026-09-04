import math
import unittest
from typing import Sequence

from app.schemas.autonomy import NavigationPoint
from app.services.autonomy import (
    AckermannPathSmoother,
    PathGeometryRejected,
)


def points(*coordinates: tuple[float, float]) -> tuple[NavigationPoint, ...]:
    return tuple(NavigationPoint(x_m=x_m, y_m=y_m) for x_m, y_m in coordinates)


class AckermannPathSmootherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.smoother = AckermannPathSmoother(
            wheelbase_m=0.18,
            max_abs_steering_angle_rad=math.radians(30),
        )

    def test_preserves_a_straight_route_and_reports_vehicle_geometry(self) -> None:
        result = self.smoother.smooth(
            points((0, 0), (2, 0)),
            start_yaw_rad=0,
            is_clear=lambda path: True,
        )

        self.assertEqual(result.path[0], NavigationPoint(x_m=0, y_m=0))
        self.assertEqual(result.path[-1], NavigationPoint(x_m=2, y_m=0))
        self.assertFalse(result.smoothed)
        self.assertEqual(result.max_curvature_per_m, 0)
        self.assertAlmostEqual(
            result.minimum_turning_radius_m, 0.18 / math.tan(math.radians(30))
        )

    def test_rounds_a_right_angle_below_the_curvature_limit(self) -> None:
        result = self.smoother.smooth(
            points((0, 0), (1, 0), (1, 1)),
            start_yaw_rad=0,
            is_clear=lambda path: True,
        )

        self.assertTrue(result.smoothed)
        self.assertGreater(len(result.path), result.raw_waypoint_count)
        self.assertLessEqual(
            result.max_curvature_per_m,
            result.curvature_limit_per_m * 1.05,
        )
        self.assertTrue(
            any(0 < point.x_m < 1 and 0 < point.y_m < 1 for point in result.path)
        )

    def test_uses_start_heading_to_create_a_tangent_route(self) -> None:
        result = self.smoother.smooth(
            points((0, 0), (1, 1)),
            start_yaw_rad=0,
            is_clear=lambda path: True,
        )

        first_segment = result.path[1]
        first_heading = math.atan2(first_segment.y_m, first_segment.x_m)
        self.assertLess(abs(first_heading), math.radians(3))
        self.assertAlmostEqual(result.initial_heading_error_rad, math.pi / 4)
        self.assertLessEqual(
            result.max_curvature_per_m,
            result.curvature_limit_per_m * 1.05,
        )

    def test_rejects_a_route_that_starts_with_a_direction_reversal(self) -> None:
        with self.assertRaisesRegex(PathGeometryRejected, "turning radius"):
            self.smoother.smooth(
                points((0, 0), (-1, 0)),
                start_yaw_rad=0,
                is_clear=lambda path: True,
            )

    def test_does_not_round_a_corner_through_blocked_space(self) -> None:
        def avoids_inside_corner(path: Sequence[NavigationPoint]) -> bool:
            return all(not (point.x_m < 0.999 and point.y_m > 0.001) for point in path)

        with self.assertRaisesRegex(PathGeometryRejected, "turning radius"):
            self.smoother.smooth(
                points((0, 0), (1, 0), (1, 1)),
                start_yaw_rad=0,
                is_clear=avoids_inside_corner,
            )

    def test_rejects_direct_line_when_safe_tangent_entry_is_blocked(self) -> None:
        with self.assertRaisesRegex(PathGeometryRejected, "current heading"):
            self.smoother.smooth(
                points((0, 0), (1, 1)),
                start_yaw_rad=0,
                is_clear=lambda path: len(path) == 2,
            )


if __name__ == "__main__":
    unittest.main()
