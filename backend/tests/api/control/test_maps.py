import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from httpx import ASGITransport, AsyncClient
from app.api import robot_deps
from app.api.control.maps import get_saved_map_store
from app.control_server import app
from app.services.autonomy import (
    LocalMappingService,
    LocalOccupancyGrid,
    LocalOccupancyGridConfig,
    TopicBus,
    RobotMode,
)
from app.services.autonomy.saved_maps import SavedMapStore
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP
from tests.services.autonomy.test_navigation_planning import grid
from tests.services.autonomy.test_saved_maps import pose


class SavedMapRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = SavedMapStore(Path(self.directory.name))
        self.saved = self.store.save("Flat", grid(10, 10), None)
        self.bus = TopicBus()
        self.mapping = LocalMappingService(
            self.bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.5,
        )
        self.motion = Mock()
        self.motion.mode = RobotMode.DISARMED
        self.motion.mode_generation = 1
        self.mission = Mock()
        self.mission.running = False
        app.dependency_overrides.update(
            {
                get_saved_map_store: lambda: self.store,
                robot_deps.get_robot_topic_bus: lambda: self.bus,
                robot_deps.get_local_mapping_service: lambda: self.mapping,
                robot_deps.get_motion_control_service: lambda: self.motion,
                robot_deps.get_navigation_execution_service: lambda: None,
                robot_deps.get_navigation_mission_service: lambda: self.mission,
            }
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.directory.cleanup()

    async def load(self):
        return await self.client.post(
            f"/px/api/maps/{self.saved.id}/load",
            json={"x_m": 1, "y_m": 1, "yaw_deg": 0},
        )

    async def test_explicit_load_then_save_and_list(self) -> None:
        self.bus.publish(LOCALIZATION_POSE, pose())
        response = await self.load()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["loaded_from_disk"])
        self.motion.set_mode.assert_not_called()
        saved = await self.client.post("/px/api/maps", json={"name": "Aligned flat"})
        self.assertEqual(saved.status_code, 200, saved.text)
        listed = await self.client.get("/px/api/maps")
        self.assertEqual(len(listed.json()), 2)

    async def test_rejects_missing_pose_armed_robot_active_mapping_and_mission(
        self,
    ) -> None:
        self.assertEqual((await self.load()).status_code, 409)
        self.bus.publish(LOCALIZATION_POSE, pose())
        self.motion.mode = RobotMode.MANUAL
        self.assertEqual((await self.load()).status_code, 409)
        self.motion.mode = RobotMode.DISARMED
        self.mission.running = True
        self.assertEqual((await self.load()).status_code, 409)
        self.mission.running = False
        self.mapping.start_session()
        self.assertEqual((await self.load()).status_code, 409)
        self.assertFalse(self.mapping.status.loaded_from_disk)

    async def test_mode_generation_rechecked_after_file_read(self) -> None:
        self.bus.publish(LOCALIZATION_POSE, pose())
        snapshot = self.store.load(self.saved.id)

        async def changing_mode(*_args: object):
            self.motion.mode_generation += 1
            return snapshot

        with patch("app.api.control.maps.asyncio.to_thread", side_effect=changing_mode):
            result = await self.load()
        self.assertEqual(result.status_code, 409, result.text)
        self.assertIn("mode changed", result.json()["detail"])
        self.assertIsNone(self.bus.latest(LOCAL_MAP))

    async def test_pose_freshness_rechecked_after_file_read(self) -> None:
        self.bus.publish(LOCALIZATION_POSE, pose())
        snapshot = self.store.load(self.saved.id)

        async def delayed_read(*_args: object):
            stale = pose()
            self.bus.publish(
                LOCALIZATION_POSE,
                stale.model_copy(
                    update={
                        "header": stale.header.model_copy(
                            update={"timestamp_monotonic_ns": 1}
                        )
                    }
                ),
            )
            await asyncio.sleep(0)
            return snapshot

        with patch("app.api.control.maps.asyncio.to_thread", side_effect=delayed_read):
            result = await self.load()
        self.assertEqual(result.status_code, 409, result.text)
        self.assertIsNone(self.bus.latest(LOCAL_MAP))

    async def test_invalid_placement_preserves_existing_map(self) -> None:
        self.mapping.load_frozen_grid(grid(3, 3))
        original = self.bus.latest(LOCAL_MAP)
        self.bus.publish(LOCALIZATION_POSE, pose())
        response = await self.client.post(
            f"/px/api/maps/{self.saved.id}/load",
            json={"x_m": -10, "y_m": -10, "yaw_deg": 0},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.bus.latest(LOCAL_MAP), original)
