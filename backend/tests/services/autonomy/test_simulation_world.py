import math
import unittest

from app.services.autonomy import (
    LineSegment2D,
    RaycastLidarConfig,
    SimulationWorld,
    WorldLidarRaycaster,
    build_simulation_world,
)


class SimulationWorldTests(unittest.TestCase):
    def test_empty_room_rays_hit_deterministic_cardinal_walls(self) -> None:
        raycaster = WorldLidarRaycaster(
            build_simulation_world("empty_room", width_m=6, height_m=4),
            RaycastLidarConfig(
                frame_id="laser",
                sensor_x_m=0,
                sensor_y_m=0,
                sensor_yaw_rad=0,
                range_min_m=0.05,
                range_max_m=10,
                angular_resolution_deg=45,
            ),
        )

        scan = raycaster.scan(
            base_x_m=0,
            base_y_m=0,
            base_yaw_rad=0,
            timestamp_ns=100,
            sequence=1,
        )

        self.assertEqual(len(scan.ranges_m), 8)
        self.assertAlmostEqual(scan.ranges_m[0], 3)
        self.assertAlmostEqual(scan.ranges_m[2], 2)
        self.assertAlmostEqual(scan.ranges_m[4], 3)
        self.assertAlmostEqual(scan.ranges_m[6], 2)
        self.assertTrue(all(value == 100 for value in scan.intensities or ()))

    def test_pose_and_sensor_transform_change_ranges_in_world_coordinates(self) -> None:
        raycaster = WorldLidarRaycaster(
            build_simulation_world("empty_room", width_m=6, height_m=4),
            RaycastLidarConfig(
                frame_id="laser",
                sensor_x_m=0.2,
                sensor_y_m=0,
                sensor_yaw_rad=0,
                range_min_m=0.05,
                range_max_m=10,
                angular_resolution_deg=45,
            ),
        )

        scan = raycaster.scan(
            base_x_m=0.5,
            base_y_m=0,
            base_yaw_rad=math.pi / 2,
            timestamp_ns=100,
            sequence=1,
        )

        self.assertAlmostEqual(scan.ranges_m[0], 1.8)
        self.assertAlmostEqual(scan.ranges_m[2], 3.5)
        self.assertAlmostEqual(scan.ranges_m[4], 2.2)
        self.assertAlmostEqual(scan.ranges_m[6], 2.5)

    def test_out_of_range_hits_use_infinity_and_zero_intensity(self) -> None:
        raycaster = WorldLidarRaycaster(
            build_simulation_world("empty_room", width_m=6, height_m=4),
            RaycastLidarConfig(
                frame_id="laser",
                sensor_x_m=0,
                sensor_y_m=0,
                sensor_yaw_rad=0,
                range_min_m=0.05,
                range_max_m=1,
                angular_resolution_deg=45,
            ),
        )

        scan = raycaster.scan(
            base_x_m=0,
            base_y_m=0,
            base_yaw_rad=0,
            timestamp_ns=100,
            sequence=1,
        )

        self.assertTrue(all(math.isinf(value) for value in scan.ranges_m))
        self.assertEqual(scan.intensities, (0.0,) * 8)

    def test_collision_uses_distance_to_finite_segments(self) -> None:
        world = SimulationWorld(
            scenario="wall",
            segments=(LineSegment2D(1, -1, 1, 1),),
        )

        self.assertTrue(world.collides_circle(0.9, 0, 0.11))
        self.assertFalse(world.collides_circle(0.8, 0, 0.11))
        self.assertFalse(world.collides_circle(1.2, 2, 0.11))

    def test_scenarios_are_reproducible_and_add_expected_obstacles(self) -> None:
        first = build_simulation_world("single_obstacle", width_m=6, height_m=6)
        second = build_simulation_world("single_obstacle", width_m=6, height_m=6)
        empty = build_simulation_world("empty_room", width_m=6, height_m=6)

        self.assertEqual(first, second)
        self.assertEqual(len(empty.segments), 4)
        self.assertEqual(len(first.segments), 8)
        self.assertTrue(first.collides_circle(1.6, 0, 0.1))
        self.assertFalse(empty.collides_circle(1.6, 0, 0.1))


if __name__ == "__main__":
    unittest.main()
