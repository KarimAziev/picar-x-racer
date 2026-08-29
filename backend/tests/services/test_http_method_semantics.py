import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.api.control.system import router as control_system_router
from app.api.endpoints.camera import router as camera_router
from app.api.endpoints.system import router as system_router
from app.services.integration.robot_communication_service import (
    RobotCommunicationService,
)
from fastapi import APIRouter
from fastapi.routing import APIRoute


def get_route_methods(router: APIRouter, path: str) -> set[str]:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path:
            return route.methods
    raise AssertionError(f"Route {path} was not found")


def get_endpoint_methods(router: APIRouter, endpoint_name: str) -> set[str]:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.endpoint.__name__ == endpoint_name:
            return route.methods
    raise AssertionError(f"Endpoint {endpoint_name} was not found")


class TestHttpMethodSemantics(unittest.TestCase):
    def assert_post_only(self, router: APIRouter, path: str) -> None:
        self.assertEqual(get_route_methods(router, path), {"POST"})

    def test_host_shutdown_is_post_only(self) -> None:
        self.assert_post_only(system_router, "/system/shutdown")

    def test_host_restart_is_post_only(self) -> None:
        self.assert_post_only(system_router, "/system/restart")

    def test_robot_service_shutdown_is_post_only(self) -> None:
        self.assert_post_only(control_system_router, "/px/api/system/shutdown")

    def test_capture_photo_is_post_only(self) -> None:
        self.assert_post_only(camera_router, "/camera/capture-photo")

    def test_camera_settings_handlers_keep_their_expected_methods(self) -> None:
        self.assertEqual(
            get_endpoint_methods(camera_router, "update_camera_settings"), {"POST"}
        )
        self.assertEqual(
            get_endpoint_methods(camera_router, "get_camera_settings"), {"GET"}
        )


class TestRobotCommunicationHttpMethods(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.integration.robot_communication_service.httpx.AsyncClient")
    async def test_robot_service_shutdown_uses_post(self, client_factory: Mock) -> None:
        client = AsyncMock()
        client.post.return_value = Mock(status_code=200)
        client_factory.return_value.__aenter__.return_value = client
        service = RobotCommunicationService("http://robot.local/")

        await service.shutdown_robot_services()

        client.post.assert_awaited_once_with(
            "http://robot.local/px/api/system/shutdown"
        )
        client.get.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
