import math
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from app.schemas.autonomy import LocalizationPose2D, MessageHeader
from app.services.autonomy import (
    LocalMappingService,
    LocalOccupancyGrid,
    LocalOccupancyGridConfig,
    TopicBus,
)
from app.services.autonomy.saved_maps import (
    MapAlignment,
    SavedMapStore,
    align_saved_grid,
)
from app.services.autonomy.topics import LOCAL_MAP
from tests.services.autonomy.test_navigation_planning import grid


def pose(*, x: float = 0, y: float = 0, yaw: float = 0) -> LocalizationPose2D:
    return LocalizationPose2D(
        header=MessageHeader(
            sequence=1, frame_id="odom", timestamp_monotonic_ns=time.monotonic_ns()
        ),
        x_m=x,
        y_m=y,
        yaw_rad=yaw,
        linear_speed_mps=0,
        yaw_rate_radps=0,
        position_variance_m2=0.01,
        yaw_variance_rad2=0.01,
        fusion_mode="wheel_imu",
    )


class SavedMapTests(unittest.TestCase):
    def test_rejects_unsupported_format_and_mismatched_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SavedMapStore(Path(directory))
            info = store.save("Map", grid(2, 2), None)
            path = Path(directory) / f"{info.id}.json"
            original = json.loads(path.read_text())
            for field, value in (("format_version", 99), ("id", "a" * 32)):
                with self.subTest(field=field):
                    path.write_text(json.dumps({**original, field: value}))
                    with self.assertRaises(ValueError):
                        store.load(info.id)

    def test_atomic_snapshot_survives_new_store_instance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "maps"
            source = grid(5, 5, data=[-1, 100] + [0] * 23, origin_yaw_rad=0.3)
            first = SavedMapStore(root).save(" Kitchen ", source, pose())
            second = SavedMapStore(root).save("Hall", source, None)
            restored = SavedMapStore(root).load(first.id)
            self.assertEqual(restored.grid, source)
            self.assertEqual(restored.name, "Kitchen")
            self.assertIsNotNone(restored.saved_pose)
            self.assertEqual(
                [entry.id for entry in SavedMapStore(root).list()],
                [second.id, first.id],
            )
            self.assertEqual(len(list(root.iterdir())), 2)

    def test_rejects_traversal_empty_maps_and_oversized_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SavedMapStore(Path(directory))
            with self.assertRaisesRegex(ValueError, "ID"):
                store.load("../config")
            with self.assertRaisesRegex(ValueError, "nonempty"):
                store.save("Unknown", grid(2, 2, data=[-1] * 4), None)
            saved = store.save("Valid", grid(2, 2), None)
            with patch.object(store, "MAX_BYTES", 10), self.assertRaisesRegex(
                ValueError, "size limit"
            ):
                store.load(saved.id)

    def test_alignment_transforms_origin_without_changing_cells(self) -> None:
        source = grid(10, 10, origin_x_m=-1, origin_y_m=-1)
        result = align_saved_grid(
            source,
            MapAlignment(x_m=1, y_m=2, yaw_deg=0),
            pose(x=5, y=6, yaw=math.pi / 2),
        )
        self.assertAlmostEqual(result.origin_x_m, 8)
        self.assertAlmostEqual(result.origin_y_m, 4)
        self.assertAlmostEqual(result.origin_yaw_rad, math.pi / 2)
        self.assertEqual(source.data, result.data)
        self.assertEqual(source.origin_x_m, -1)

    def test_alignment_respects_rotated_saved_grid(self) -> None:
        source = grid(3, 3, origin_yaw_rad=math.pi / 2)
        aligned = align_saved_grid(
            source, MapAlignment(x_m=-0.5, y_m=0.5, yaw_deg=90), pose()
        )
        self.assertAlmostEqual(aligned.origin_yaw_rad, 0)
        self.assertAlmostEqual(aligned.origin_x_m, -0.5)
        self.assertAlmostEqual(aligned.origin_y_m, -0.5)

    def test_alignment_rejects_unknown_occupied_and_outside_placements(self) -> None:
        source = grid(2, 2, data=[0, -1, 100, 0])
        for x, y in ((1.5, 0.5), (0.5, 1.5), (-1, 0), (2, 0)):
            with self.subTest(x=x, y=y), self.assertRaises(ValueError):
                align_saved_grid(source, MapAlignment(x_m=x, y_m=y, yaw_deg=0), pose())


class LoadedMappingTests(unittest.IsolatedAsyncioTestCase):
    async def test_loaded_map_is_frozen_and_clear_returns_to_normal_mapping(
        self,
    ) -> None:
        bus = TopicBus()
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.5,
        )
        loaded = service.load_frozen_grid(grid(3, 3, origin_yaw_rad=0.5))
        self.assertTrue(loaded.loaded_from_disk)
        self.assertTrue(loaded.has_map)
        self.assertEqual(loaded.state.value, "paused")
        snapshot = bus.latest(LOCAL_MAP)
        assert snapshot is not None
        self.assertEqual(snapshot.origin_yaw_rad, 0.5)
        with self.assertRaisesRegex(ValueError, "frozen"):
            service.start_session()
        service.finish_session()
        self.assertTrue(service.status.loaded_from_disk)
        service.clear_map()
        self.assertFalse(service.status.loaded_from_disk)
        service.start_session()
        self.assertEqual(service.status.state.value, "active")
