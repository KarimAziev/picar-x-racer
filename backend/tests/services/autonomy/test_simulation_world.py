import math
import unittest

from app.services.autonomy import (
    LineSegment2D,
    RaycastLidarConfig,
    SegmentSpatialIndex,
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

    def test_spatial_index_matches_nearby_distance_and_caps_far_queries(self) -> None:
        segments = (
            LineSegment2D(1, -1, 1, 1),
            LineSegment2D(-4, -2, -4, 2),
        )
        index = SegmentSpatialIndex(segments, max_distance=0.5)

        self.assertAlmostEqual(index.distance_to_nearest(0.8, 0.25), 0.2)
        self.assertEqual(index.distance_to_nearest(0, 0), 0.5)

    def test_spatial_index_matches_brute_force_apartment_distances(self) -> None:
        world = build_simulation_world("apartment", width_m=8.81, height_m=5.31)
        index = SegmentSpatialIndex(world.segments, max_distance=0.5)

        for x_m, y_m in (
            (-4.2, -2.4),
            (-1.3, -1.9),
            (-0.8, 0.9),
            (0.0, 0.0),
            (1.36, 0.0),
            (2.2, 1.4),
            (4.1, 2.4),
        ):
            expected = min(
                0.5,
                world.distance_to_nearest_segment(x_m, y_m),
            )
            self.assertAlmostEqual(
                index.distance_to_nearest(x_m, y_m),
                expected,
            )

    def test_scenarios_are_reproducible_and_add_expected_obstacles(self) -> None:
        first = build_simulation_world("single_obstacle", width_m=6, height_m=6)
        second = build_simulation_world("single_obstacle", width_m=6, height_m=6)
        empty = build_simulation_world("empty_room", width_m=6, height_m=6)

        self.assertEqual(first, second)
        self.assertEqual(len(empty.segments), 4)
        self.assertEqual(len(first.segments), 8)
        self.assertTrue(first.collides_circle(1.6, 0, 0.1))
        self.assertFalse(empty.collides_circle(1.6, 0, 0.1))

    def test_apartment_contains_scaled_rooms_doorways_and_furniture(self) -> None:
        world = build_simulation_world(
            "apartment",
            width_m=8.81,
            height_m=5.31,
        )

        self.assertEqual(world.scenario, "apartment")
        self.assertEqual(len(world.solid_rectangles), 15)
        self.assertEqual(len(world.segments), 72)
        # The supplied floor-plan robot position is clear, but nearby room
        # partitions and the central bed remain collidable.
        self.assertFalse(world.collides_circle(1.36, 0, 0.12))
        self.assertTrue(world.collides_circle(-1.17, 0, 0.12))
        self.assertTrue(world.collides_circle(-0.75, 1.0, 0.12))
        # The lower doorway through the kitchen divider stays traversable.
        self.assertFalse(world.collides_circle(-1.17, -2.0, 0.12))

    def test_apartment_lidar_observes_interior_geometry(self) -> None:
        raycaster = WorldLidarRaycaster(
            build_simulation_world("apartment", width_m=8.81, height_m=5.31),
            RaycastLidarConfig(
                frame_id="laser",
                sensor_x_m=0,
                sensor_y_m=0,
                sensor_yaw_rad=0,
                range_min_m=0.05,
                range_max_m=12,
                angular_resolution_deg=1,
            ),
        )

        scan = raycaster.scan(
            base_x_m=1.36,
            base_y_m=0,
            base_yaw_rad=math.pi,
            timestamp_ns=100,
            sequence=1,
        )

        self.assertEqual(len(scan.ranges_m), 360)
        self.assertTrue(all(math.isfinite(distance) for distance in scan.ranges_m))
        self.assertLess(min(scan.ranges_m), 0.5)
        self.assertGreater(max(scan.ranges_m), 2.0)


if __name__ == "__main__":
    unittest.main()
